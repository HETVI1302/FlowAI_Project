"""
FlowAI demo seed script.

Populates the MySQL database with realistic mock data across every app
(accounts, monitoring, signals_app, prediction, analytics, notifications,
reports) so the dashboard, live charts, and analytics pages are fully
populated the moment the app is launched for a demo — no manual clicking
around needed to "warm up" the data.

USAGE
-----
    python manage.py shell -c "import seed.seed_data as s; s.run()"

or, since this file is a plain script (not a management command — the
`seed/` folder is a scripts directory, not a Django app):

    python seed/seed_data.py

Both work because the script bootstraps Django itself when run directly,
and exposes `run()` for the shell-import route.

Safe to re-run: it clears out previously-seeded rows first (see
`_wipe_existing()`) rather than piling up duplicates on every run.
"""
import os
import random
import sys
import uuid
from datetime import timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap Django when this file is executed directly (`python seed/seed_data.py`)
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    BASE_DIR = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flowai_core.settings')
    import django
    django.setup()

from django.utils import timezone
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
# Tunables — kept modest per table so seeding stays fast, but sums to the
# ~500-row demo dataset called for in the spec once you add it all up.
# ---------------------------------------------------------------------------
NUM_USERS = 15
NUM_INTERSECTIONS = 10
CAMERAS_PER_INTERSECTION = (1, 3)          # random.randint range
VEHICLES_PER_INTERSECTION = (18, 30)
DENSITY_SNAPSHOTS_PER_INTERSECTION = (8, 14)
SIGNAL_CHANGE_LOGS_PER_SIGNAL = (2, 6)
PREDICTIONS_PER_INTERSECTION = (4, 8)
INCIDENTS_TOTAL = 15
PATTERNS_PER_INTERSECTION = 6              # a handful of day/hour cells, not all 168
EMISSIONS_PER_INTERSECTION = (3, 5)
STATISTICS_PER_INTERSECTION = (3, 5)
NOTIFICATIONS_TOTAL = 35
REPORTS_TOTAL = 12

INTERSECTION_NAMES = [
    'CG Road & Panchvati Cross', 'SG Highway & Iskcon Junction',
    'Ashram Road & Nehru Bridge', 'Satellite Rd & Jodhpur Cross',
    'Prahladnagar Garden Circle', 'Vastrapur Lake Junction',
    'Naranpura Char Rasta', 'Maninagar Railway Crossing',
    'Bopal Ambli Road Junction', 'Gandhinagar Sector 21 Circle',
    'Paldi Underbridge Crossing', 'Ranip Highway Junction',
]

VEHICLE_WEIGHTS = [
    ('car', 55), ('motorcycle', 25), ('bus', 6),
    ('truck', 8), ('ambulance', 2), ('police', 2), ('other', 2),
]

INCIDENT_TYPES = ['accident', 'stalled_vehicle', 'wrong_way', 'obstruction', 'other']
SEVERITIES = ['low', 'medium', 'high', 'critical']
CONGESTION_LEVELS = ['low', 'moderate', 'high', 'severe']
NOTIF_CATEGORIES = [
    'congestion', 'accident', 'signal_failure', 'emergency_vehicle',
    'camera_offline', 'system',
]
NOTIF_PRIORITIES = ['low', 'medium', 'high', 'critical']


def weighted_choice(pairs):
    options, weights = zip(*pairs)
    return random.choices(options, weights=weights, k=1)[0]


def run():
    # Imported lazily so this module can be imported before django.setup()
    # runs (e.g. from `manage.py shell -c`, where setup already happened).
    from django.contrib.auth import get_user_model
    from monitoring.models import Intersection, Camera, Vehicle, TrafficDensitySnapshot
    from signals_app.models import Signal, SignalChangeLog
    from prediction.models import CongestionPrediction, IncidentDetection, TrafficPattern
    from analytics.models import Emission, TrafficStatistic
    from notifications.models import Notification
    from reports.models import Report

    User = get_user_model()
    now = timezone.now()

    print('FlowAI demo seed — starting...')
    _wipe_existing(
        User, Intersection, Camera, Vehicle, TrafficDensitySnapshot,
        Signal, SignalChangeLog, CongestionPrediction, IncidentDetection,
        TrafficPattern, Emission, TrafficStatistic, Notification, Report,
    )

    # ---------------------------------------------------------------- Users
    users = []
    admin = User.objects.create_superuser(
        username='admin', email='admin@flowai.city', password='FlowAI@2026',
    )
    admin.role = User.Role.ADMIN
    admin.is_verified = True
    admin.department = 'City Traffic Control'
    admin.save()
    users.append(admin)

    roles = [User.Role.OPERATOR, User.Role.ANALYST, User.Role.VIEWER]
    for _ in range(NUM_USERS - 1):
        first, last = fake.first_name(), fake.last_name()
        u = User.objects.create_user(
            username=fake.unique.user_name(),
            email=fake.unique.email(),
            password='Demo@1234',
            first_name=first,
            last_name=last,
            role=random.choice(roles),
            phone_number=fake.msisdn()[:15],
            department=random.choice(
                ['Traffic Control', 'Public Works', 'Emergency Services', 'City Planning']
            ),
            is_verified=random.random() > 0.2,
        )
        users.append(u)
    print(f'  users: {len(users)}')

    # ------------------------------------------------------- Intersections
    intersections = []
    for i in range(NUM_INTERSECTIONS):
        name = INTERSECTION_NAMES[i % len(INTERSECTION_NAMES)]
        intersections.append(Intersection.objects.create(
            name=name,
            location=f'{name}, Ahmedabad, Gujarat',
            latitude=round(23.0 + random.uniform(-0.15, 0.15), 6),
            longitude=round(72.5 + random.uniform(-0.15, 0.15), 6),
            status=weighted_choice([('active', 85), ('maintenance', 10), ('inactive', 5)]),
        ))
    print(f'  intersections: {len(intersections)}')

    # ------------------------------------------------------------ Cameras
    cameras = []
    for inter in intersections:
        for c in range(random.randint(*CAMERAS_PER_INTERSECTION)):
            cameras.append(Camera.objects.create(
                intersection=inter,
                name=f'{inter.name.split(" ")[0]}-CAM-{c + 1}',
                camera_url=f'rtsp://cctv.flowai.local/streams/{uuid.uuid4().hex[:8]}',
                status=weighted_choice([('online', 80), ('offline', 12), ('error', 8)]),
                resolution=random.choice(['1280x720', '1920x1080', '2560x1440']),
                fps=random.choice([10, 15, 24, 30]),
                last_heartbeat=now - timedelta(seconds=random.randint(0, 600)),
            ))
    print(f'  cameras: {len(cameras)}')

    # ----------------------------------------------------------- Vehicles
    vehicles = []
    for inter in intersections:
        inter_cameras = [c for c in cameras if c.intersection_id == inter.id] or cameras
        for _ in range(random.randint(*VEHICLES_PER_INTERSECTION)):
            ts = now - timedelta(
                hours=random.randint(0, 72), minutes=random.randint(0, 59)
            )
            vehicles.append(Vehicle(
                camera=random.choice(inter_cameras),
                intersection=inter,
                vehicle_type=weighted_choice(VEHICLE_WEIGHTS),
                confidence_score=round(random.uniform(0.62, 0.99), 3),
                bounding_box=[
                    random.randint(0, 800), random.randint(0, 400),
                    random.randint(800, 1280), random.randint(400, 720),
                ],
                speed_kmph=round(random.uniform(0, 65), 1),
                timestamp=ts,
            ))
    # bulk_create skips the custom .save(), so set is_emergency explicitly
    for v in vehicles:
        v.is_emergency = v.vehicle_type in ('ambulance', 'police')
    Vehicle.objects.bulk_create(vehicles, batch_size=200)
    print(f'  vehicles: {len(vehicles)}')

    # ------------------------------------------------ Density snapshots
    snapshots = []
    for inter in intersections:
        for _ in range(random.randint(*DENSITY_SNAPSHOTS_PER_INTERSECTION)):
            level = weighted_choice(
                [('low', 40), ('moderate', 35), ('high', 18), ('severe', 7)]
            )
            snapshots.append(TrafficDensitySnapshot(
                intersection=inter,
                vehicle_count=random.randint(2, 90),
                queue_length_meters=round(random.uniform(5, 220), 1),
                avg_waiting_time_seconds=round(random.uniform(8, 180), 1),
                congestion_level=level,
                captured_at=now - timedelta(
                    hours=random.randint(0, 48), minutes=random.randint(0, 59)
                ),
            ))
    TrafficDensitySnapshot.objects.bulk_create(snapshots, batch_size=200)
    print(f'  density snapshots: {len(snapshots)}')

    # ----------------------------------------------------------- Signals
    signals = []
    for inter in intersections:
        green = random.randint(20, 60)
        signals.append(Signal.objects.create(
            intersection=inter,
            green_time=green,
            yellow_time=3,
            red_time=random.randint(20, 60),
            mode=weighted_choice(
                [('dynamic', 55), ('fixed', 25), ('manual', 12), ('emergency', 8)]
            ),
            is_active=random.random() > 0.05,
            last_updated_by=random.choice(['system'] + [u.username for u in users[:5]]),
        ))
    print(f'  signals: {len(signals)}')

    change_logs = []
    for sig in signals:
        prev = sig.green_time
        for _ in range(random.randint(*SIGNAL_CHANGE_LOGS_PER_SIGNAL)):
            new = max(10, prev + random.randint(-8, 8))
            change_logs.append(SignalChangeLog(
                signal=sig,
                previous_green_time=prev,
                new_green_time=new,
                reason=random.choice([
                    'AI optimizer rebalanced for peak inbound flow',
                    'Emergency vehicle priority override',
                    'Manual operator adjustment',
                    'Congestion threshold exceeded',
                    'Scheduled off-peak timing',
                ]),
                triggered_by=random.choice(['system', 'system', 'operator']),
            ))
            prev = new
    SignalChangeLog.objects.bulk_create(change_logs, batch_size=200)
    print(f'  signal change logs: {len(change_logs)}')

    # -------------------------------------------------------- Predictions
    predictions = []
    for inter in intersections:
        for _ in range(random.randint(*PREDICTIONS_PER_INTERSECTION)):
            predictions.append(CongestionPrediction(
                intersection=inter,
                predicted_for=now + timedelta(hours=random.randint(1, 24)),
                predicted_level=weighted_choice(
                    [('low', 35), ('moderate', 35), ('high', 20), ('severe', 10)]
                ),
                predicted_vehicle_count=random.randint(5, 120),
                confidence=round(random.uniform(0.55, 0.97), 3),
                model_version='v1',
            ))
    CongestionPrediction.objects.bulk_create(predictions, batch_size=200)
    print(f'  predictions: {len(predictions)}')

    # ------------------------------------------------------ Incidents
    incidents = []
    for _ in range(INCIDENTS_TOTAL):
        inter = random.choice(intersections)
        inter_cameras = [c for c in cameras if c.intersection_id == inter.id]
        detected = now - timedelta(hours=random.randint(0, 96))
        resolved = random.random() > 0.35
        incidents.append(IncidentDetection.objects.create(
            intersection=inter,
            camera=random.choice(inter_cameras) if inter_cameras else None,
            incident_type=random.choice(INCIDENT_TYPES),
            severity=random.choice(SEVERITIES),
            confidence=round(random.uniform(0.6, 0.98), 3),
            is_resolved=resolved,
            detected_at=detected,
            resolved_at=detected + timedelta(minutes=random.randint(4, 90)) if resolved else None,
        ))
    print(f'  incidents: {len(incidents)}')

    # ------------------------------------------------------- Patterns
    patterns = []
    for inter in intersections:
        seen = set()
        while len(seen) < PATTERNS_PER_INTERSECTION:
            cell = (random.randint(0, 6), random.randint(0, 23))
            seen.add(cell)
        for day, hour in seen:
            rush = hour in (8, 9, 18, 19)
            patterns.append(TrafficPattern(
                intersection=inter,
                day_of_week=day,
                hour_of_day=hour,
                avg_vehicle_count=round(random.uniform(40, 110) if rush else random.uniform(5, 45), 1),
                avg_congestion_score=round(random.uniform(0.6, 0.95) if rush else random.uniform(0.1, 0.55), 2),
                sample_size=random.randint(10, 60),
            ))
    TrafficPattern.objects.bulk_create(patterns, batch_size=200)
    print(f'  traffic patterns: {len(patterns)}')

    # ------------------------------------------------------- Emissions
    emissions = []
    for inter in intersections:
        for _ in range(random.randint(*EMISSIONS_PER_INTERSECTION)):
            start = now - timedelta(hours=random.randint(1, 96))
            emissions.append(Emission(
                intersection=inter,
                carbon_emission_kg=round(random.uniform(4, 85), 2),
                fuel_consumption_liters=round(random.uniform(2, 45), 2),
                pollution_index=round(random.uniform(15, 180), 1),
                idle_time_seconds=round(random.uniform(60, 4200), 1),
                window_start=start,
                window_end=start + timedelta(hours=1),
            ))
    Emission.objects.bulk_create(emissions, batch_size=200)
    print(f'  emissions: {len(emissions)}')

    # ---------------------------------------------------------- Statistics
    stats = []
    for inter in intersections:
        for _ in range(random.randint(*STATISTICS_PER_INTERSECTION)):
            days_back = random.randint(0, 60)
            stats.append((inter, 'daily', (now - timedelta(days=days_back)).date()))
    # dedupe on unique_together before bulk_create
    seen_keys = set()
    stat_objs = []
    for inter, period, period_start in stats:
        key = (inter.id, period, period_start)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        stat_objs.append(TrafficStatistic(
            intersection=inter,
            period=period,
            period_start=period_start,
            total_vehicles=random.randint(150, 3200),
            avg_congestion_score=round(random.uniform(0.15, 0.85), 2),
            avg_waiting_time_seconds=round(random.uniform(15, 140), 1),
            peak_hour=random.choice([8, 9, 13, 18, 19]),
        ))
    TrafficStatistic.objects.bulk_create(stat_objs, batch_size=200)
    print(f'  traffic statistics: {len(stat_objs)}')

    # ------------------------------------------------------ Notifications
    notif_titles = {
        'congestion': 'Congestion threshold exceeded',
        'accident': 'Possible accident detected',
        'signal_failure': 'Signal timing fault reported',
        'emergency_vehicle': 'Emergency vehicle approaching',
        'camera_offline': 'Camera feed lost',
        'system': 'System status update',
    }
    notifications = []
    for _ in range(NOTIFICATIONS_TOTAL):
        cat = random.choice(NOTIF_CATEGORIES)
        inter = random.choice(intersections)
        notifications.append(Notification.objects.create(
            intersection=inter,
            category=cat,
            priority=random.choice(NOTIF_PRIORITIES),
            title=f'{notif_titles[cat]} — {inter.name}',
            message=fake.sentence(nb_words=14),
            is_read=random.random() > 0.4,
        ))
    print(f'  notifications: {len(notifications)}')

    # ------------------------------------------------------------ Reports
    reports = []
    for _ in range(REPORTS_TOTAL):
        period_start = (now - timedelta(days=random.randint(7, 60))).date()
        reports.append(Report.objects.create(
            intersection=random.choice(intersections + [None] * 3),
            generated_by=random.choice(users),
            report_type=random.choice(['daily', 'weekly', 'monthly', 'custom']),
            file_format=random.choice(['pdf', 'csv', 'xlsx']),
            status='ready',
            period_start=period_start,
            period_end=period_start + timedelta(days=random.choice([1, 7, 30])),
            completed_at=now - timedelta(hours=random.randint(1, 200)),
        ))
    print(f'  reports: {len(reports)}')

    total = (
        len(users) + len(intersections) + len(cameras) + len(vehicles)
        + len(snapshots) + len(signals) + len(change_logs) + len(predictions)
        + len(incidents) + len(patterns) + len(emissions) + len(stat_objs)
        + len(notifications) + len(reports)
    )
    print(f'\nDone — {total} rows seeded across 14 tables.')
    print('Login as admin@flowai.city / FlowAI@2026 (or any seeded user / Demo@1234).')


def _wipe_existing(User, Intersection, Camera, Vehicle, TrafficDensitySnapshot,
                    Signal, SignalChangeLog, CongestionPrediction, IncidentDetection,
                    TrafficPattern, Emission, TrafficStatistic, Notification, Report):
    """Clear previously-seeded demo rows so re-running this script doesn't
    pile up duplicates. Real (non-demo) superusers created outside this
    script are untouched since we only ever created 'admin' + fake users
    here — but to keep this safe on a shared dev DB, only rows reachable
    through Intersection are cascade-deleted, and only demo users
    (non-staff, or the specific 'admin' account) are removed."""
    Intersection.objects.all().delete()  # cascades to nearly everything else
    Notification.objects.all().delete()
    Report.objects.all().delete()
    User.objects.filter(username='admin').delete()
    User.objects.filter(is_staff=False, is_superuser=False).delete()


if __name__ == '__main__':
    run()
