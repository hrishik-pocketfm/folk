"""
One-time command to merge students who share the same phone number under the same user.

Merge rules:
  - Keep the student with the most sessions (tie-break: latest created_at)
  - Transfer all sessions from duplicates → primary (L1/L2/L3 stay unique; FOLK carries over all)
  - Take the highest rating across all duplicates
  - Use the most recently created name/occupation/notes (if non-empty)
  - Delete the duplicate records after merging
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Student, StudentSession, RATING_PRIORITY, higher_rating


class Command(BaseCommand):
    help = 'Merge duplicate students (same phone number, same user) into a single record'

    def handle(self, *args, **options):
        total_merged = 0

        # Find all (user, phone) pairs with more than one student
        from django.db.models import Count
        dupes = (
            Student.objects
            .exclude(phone_number='')
            .values('created_by', 'phone_number')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
        )

        for d in dupes:
            with transaction.atomic():
                group = list(
                    Student.objects
                    .filter(created_by=d['created_by'], phone_number=d['phone_number'])
                    .prefetch_related('sessions')
                    .order_by('-created_at')
                )

                # Primary = most sessions; tie-break = latest created
                primary = max(group, key=lambda s: (s.sessions.count(), s.created_at))
                duplicates = [s for s in group if s.pk != primary.pk]

                # Best name/occupation/notes = from most recently created non-empty
                for dup in sorted(duplicates, key=lambda s: s.created_at, reverse=True):
                    if dup.name:
                        primary.name = dup.name
                        break
                for dup in sorted(duplicates, key=lambda s: s.created_at, reverse=True):
                    if dup.occupation and not primary.occupation:
                        primary.occupation = dup.occupation
                        break
                for dup in sorted(duplicates, key=lambda s: s.created_at, reverse=True):
                    if dup.notes and not primary.notes:
                        primary.notes = dup.notes
                        break

                # Highest rating
                for dup in duplicates:
                    primary.rating = higher_rating(primary.rating, dup.rating)

                primary.save()

                # Transfer sessions
                existing_types = set(primary.sessions.values_list('session_type', flat=True))

                for dup in duplicates:
                    for sess in dup.sessions.all():
                        if sess.session_type == 'FOLK':
                            # FOLK is continuous — always transfer
                            StudentSession.objects.create(
                                student=primary,
                                session_type='FOLK',
                                date_attended=sess.date_attended,
                                added_by=sess.added_by,
                            )
                        else:
                            if sess.session_type not in existing_types:
                                sess.student = primary
                                sess.save()
                                existing_types.add(sess.session_type)
                            # else: duplicate L1/L2/L3 — skip

                # Delete duplicates
                names = [d.name for d in duplicates]
                for dup in duplicates:
                    dup.delete()

                total_merged += len(duplicates)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Merged {len(duplicates)} duplicate(s) into "{primary.name}" '
                        f'(phone: {primary.phone_number}) — absorbed: {names}'
                    )
                )

        if total_merged == 0:
            self.stdout.write(self.style.WARNING('No duplicate students found.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nDone. Total records merged: {total_merged}'))
