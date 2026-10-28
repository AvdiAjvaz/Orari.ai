from collections import Counter
from typing import Literal
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from ortools.sat.python import cp_model

class Teacher(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    unavailable: list[int] = Field(default_factory=list)
    max_hours: int | None = Field(default=None, ge=0, le=84)

class Lesson(BaseModel):
    classroom: str = Field(min_length=1, max_length=80)
    subject: str = Field(min_length=1, max_length=80)
    teacher: str
    hours: int = Field(ge=1, le=40)
    room: str = ''
    max_per_day: int | None = Field(default=None, ge=1, le=12)
    double_periods: int = Field(default=0, ge=0, le=20)

    @model_validator(mode='after')
    def blocks_fit(self):
        if self.double_periods * 2 > self.hours:
            raise ValueError('Blloqet dyshe kërkojnë më shumë orë se ngarkesa javore.')
        return self

class ClassRule(BaseModel):
    classroom: str = Field(min_length=1, max_length=80)
    min_daily_hours: int | None = Field(default=None, ge=0, le=12)
    max_daily_hours: int | None = Field(default=None, ge=1, le=12)

class School(BaseModel):
    days: int = Field(default=5, ge=1, le=7)
    periods: int = Field(default=6, ge=1, le=12)
    teachers: list[Teacher] = Field(min_length=1, max_length=100)
    lessons: list[Lesson] = Field(min_length=1, max_length=250)
    preferred_friday_hours: int | None = Field(default=None, ge=0, le=12)
    min_daily_hours: int = Field(default=0, ge=0, le=12)
    max_daily_hours: int | None = Field(default=None, ge=1, le=12)
    max_subject_per_day: int | None = Field(default=None, ge=1, le=12)
    classes: list[str] = Field(default_factory=list, max_length=250)
    class_rules: list[ClassRule] = Field(default_factory=list, max_length=250)
    time_limit: float = Field(default=10, ge=1, le=30)

    @model_validator(mode='after')
    def references(self):
        if self.preferred_friday_hours is not None and (self.days < 5 or self.preferred_friday_hours > self.periods):
            raise ValueError('Preferenca e së premtes kërkon të paktën 5 ditë dhe orë brenda ditës shkollore.')
        names = [t.name for t in self.teachers]
        if len(set(names)) != len(names):
            raise ValueError('Emrat e profesorëve duhet të jenë unikë.')
        if any(l.teacher not in names for l in self.lessons):
            raise ValueError('Çdo angazhim duhet të ketë profesor të regjistruar.')
        if any(s < 0 or s >= self.days*self.periods for t in self.teachers for s in t.unavailable):
            raise ValueError('Termini i padisponueshëm është jashtë javës.')
        if sum(l.hours for l in self.lessons) > 1200:
            raise ValueError('Versioni fillestar përkrah deri në 1200 orë.')
        if len(set(self.classes)) != len(self.classes) or any(not c or len(c) > 80 for c in self.classes):
            raise ValueError('Lista e klasave duhet të ketë emra unikë dhe të vlefshëm.')
        rule_names = [rule.classroom for rule in self.class_rules]
        if len(set(rule_names)) != len(rule_names):
            raise ValueError('Rregullat e klasës duhet të jenë unike.')
        if self.min_daily_hours > (self.max_daily_hours if self.max_daily_hours is not None else self.periods):
            raise ValueError('Minimumi ditor nuk mund të jetë mbi maksimumin ditor.')
        for classroom in classrooms(self):
            low, high = daily_bounds(self, classroom)
            if low > high or high > self.periods:
                raise ValueError(f'{classroom}: kufijtë ditorë nuk përputhen me orët e shkollës.')
        return self

def classrooms(school):
    return set(school.classes) | {lesson.classroom for lesson in school.lessons} | {r.classroom for r in school.class_rules}

def daily_bounds(school, classroom):
    rule = next((r for r in school.class_rules if r.classroom == classroom), None)
    low = rule.min_daily_hours if rule and rule.min_daily_hours is not None else school.min_daily_hours
    high = rule.max_daily_hours if rule and rule.max_daily_hours is not None else school.max_daily_hours
    return low, high if high is not None else school.periods

def subject_limit(school, classroom, subject):
    overrides = [l.max_per_day for l in school.lessons if l.classroom == classroom and l.subject == subject and l.max_per_day is not None]
    if overrides:
        return min(overrides)
    # Unknown subjects in the photo are not evidence that these are the same subject.
    return school.max_subject_per_day if subject != 'Lëndë e papërcaktuar' else None

def verify(school, entries):
    errors, occupied = [], set()
    counts = Counter()
    unavailable = {t.name: set(t.unavailable) for t in school.teachers}
    for entry in entries:
        i, slot = entry['lesson'], entry['slot']
        if not 0 <= i < len(school.lessons) or not 0 <= slot < school.days*school.periods:
            errors.append('Termin ose angazhim i pavlefshëm.'); continue
        lesson = school.lessons[i]
        counts[i] += 1
        if slot in unavailable[lesson.teacher]:
            errors.append('Profesori është i padisponueshëm.')
        for kind, value in [('class', lesson.classroom), ('teacher', lesson.teacher), ('room', lesson.room)]:
            if not value: continue
            key = (kind, value, slot)
            if key in occupied: errors.append(f'Përplasje: {value}.')
            occupied.add(key)
    if any(counts[i] != lesson.hours for i, lesson in enumerate(school.lessons)):
        errors.append('Numri i orëve javore nuk përputhet.')
    for classroom in classrooms(school):
        for day in range(school.days):
            periods = [p for p in range(school.periods) if ('class', classroom, day * school.periods + p) in occupied]
            low, high = daily_bounds(school, classroom)
            if not low <= len(periods) <= high:
                errors.append(f'{classroom}, dita {day + 1}: ngarkesa ditore duhet të jetë {low}–{high} orë.')
            if periods and periods != list(range(periods[-1] + 1)):
                errors.append(f'{classroom}, dita {day + 1}: mësimi duhet të nisë në orën e parë dhe të vazhdojë pa orë të zbrazëta.')
    valid = [e for e in entries if 0 <= e['lesson'] < len(school.lessons) and 0 <= e['slot'] < school.days * school.periods]
    subject_counts = Counter((school.lessons[e['lesson']].classroom, school.lessons[e['lesson']].subject, e['slot'] // school.periods) for e in valid)
    for (classroom, subject, day), count in subject_counts.items():
        limit = subject_limit(school, classroom, subject)
        if limit is not None and count > limit:
            errors.append(f'{classroom}, {subject}, dita {day + 1}: tejkalohet kufiri {limit} orë/ditë.')
    for i, lesson in enumerate(school.lessons):
        pairs = 0
        for day in range(school.days):
            assigned = {e['slot'] % school.periods for e in valid if e['lesson'] == i and e['slot'] // school.periods == day}
            run = 0
            for period in range(school.periods + 1):
                if period in assigned:
                    run += 1
                else:
                    pairs += run // 2
                    run = 0
        if pairs < lesson.double_periods:
            errors.append(f'{lesson.classroom}, {lesson.subject}: mungojnë blloqet dyshe të kërkuara.')
    teacher_hours = Counter()
    for i, count in counts.items():
        teacher_hours[school.lessons[i].teacher] += count
    for teacher in school.teachers:
        if teacher.max_hours is not None and teacher_hours[teacher.name] > teacher.max_hours:
            errors.append(f'{teacher.name}: tejkalohet maksimumi javor prej {teacher.max_hours} orësh.')
    return errors

def generate(school):
    slots = range(school.days * school.periods)
    issues = []
    for kind in ('classroom', 'teacher', 'room'):
        demand = Counter()
        for lesson in school.lessons:
            if getattr(lesson, kind): demand[getattr(lesson, kind)] += lesson.hours
        for name, hours in demand.items():
            capacity = len(slots)
            if kind == 'teacher':
                teacher = next(t for t in school.teachers if t.name == name)
                capacity -= len(set(teacher.unavailable))
                if teacher.max_hours is not None and hours > teacher.max_hours:
                    issues.append(f'{name}: {hours} orë të caktuara, por maksimumi javor është {teacher.max_hours}. Zvogëlo ngarkesën ose ndrysho kufirin.')
            if hours > capacity: issues.append(f'{name}: {hours} orë të kërkuara, vetëm {capacity} termine të lira.')
    for classroom in classrooms(school):
        hours = sum(l.hours for l in school.lessons if l.classroom == classroom)
        low, high = daily_bounds(school, classroom)
        if not low * school.days <= hours <= high * school.days:
            issues.append(f'{classroom}: {hours} orë javore nuk përputhen me kufijtë {low}–{high} orë për secilën nga {school.days} ditët.')
    for classroom, subject in {(l.classroom, l.subject) for l in school.lessons}:
        limit = subject_limit(school, classroom, subject)
        matching = [l for l in school.lessons if l.classroom == classroom and l.subject == subject]
        if limit is not None and sum(l.hours for l in matching) > limit * school.days:
            issues.append(f'{classroom}, {subject}: ngarkesa tejkalon kufirin {limit} orë/ditë për {school.days} ditë.')
        if limit == 1 and any(l.double_periods for l in matching):
            issues.append(f'{classroom}, {subject}: blloqet dyshe kërkojnë kufi ditor së paku 2.')
    if issues: return {'status': 'infeasible', 'issues': issues, 'entries': []}
    model = cp_model.CpModel()
    x = {(i, s): model.new_bool_var(f'x_{i}_{s}') for i in range(len(school.lessons)) for s in slots}
    unavailable = {t.name: set(t.unavailable) for t in school.teachers}
    for i, lesson in enumerate(school.lessons):
        model.add(sum(x[i, s] for s in slots) == lesson.hours)
        for s in unavailable[lesson.teacher]: model.add(x[i, s] == 0)
    for i, lesson in enumerate(school.lessons):
        if not lesson.double_periods:
            continue
        starts = {}
        for day in range(school.days):
            for period in range(school.periods - 1):
                slot = day * school.periods + period
                start = model.new_bool_var(f'pair_{i}_{slot}')
                starts[slot] = start
                model.add(start <= x[i, slot])
                model.add(start <= x[i, slot + 1])
        model.add(sum(starts.values()) == lesson.double_periods)
        for slot in slots:
            covering = [starts[s] for s in (slot - 1, slot) if s in starts and s // school.periods == slot // school.periods]
            model.add(sum(covering) <= x[i, slot])
    for kind in ('classroom', 'teacher', 'room'):
        for value in {getattr(l, kind) for l in school.lessons} - {''}:
            indices = [i for i, l in enumerate(school.lessons) if getattr(l, kind) == value]
            for s in slots: model.add(sum(x[i, s] for i in indices) <= 1)
    # Class occupancy is a daily prefix: 1,1,...,1,0,...,0.
    # This prohibits both late starts and internal holes; teachers may still arrive later.
    for classroom in classrooms(school):
        indices = [i for i, lesson in enumerate(school.lessons) if lesson.classroom == classroom]
        for day in range(school.days):
            low, high = daily_bounds(school, classroom)
            total = sum(x[i, slot] for i in indices for slot in range(day * school.periods, (day + 1) * school.periods))
            model.add(total >= low)
            model.add(total <= high)
            for period in range(school.periods - 1):
                slot = day * school.periods + period
                model.add(sum(x[i, slot] for i in indices) >= sum(x[i, slot + 1] for i in indices))
    for teacher in school.teachers:
        if teacher.max_hours is not None:
            indices = [i for i, lesson in enumerate(school.lessons) if lesson.teacher == teacher.name]
            model.add(sum(x[i, s] for i in indices for s in slots) <= teacher.max_hours)
    penalties = []
    # Prefer spreading each class/subject across days, even if taught by different teachers.
    for classroom, subject in {(l.classroom, l.subject) for l in school.lessons}:
        indices = [i for i,l in enumerate(school.lessons) if (l.classroom,l.subject)==(classroom,subject)]
        for d in range(school.days):
            limit = subject_limit(school, classroom, subject)
            if limit is not None:
                model.add(sum(x[i,s] for i in indices for s in range(d*school.periods,(d+1)*school.periods)) <= limit)
            extra = model.new_int_var(0, school.periods, 'repeated_subject')
            model.add(extra >= sum(x[i,s] for i in indices for s in range(d*school.periods,(d+1)*school.periods))-1)
            penalties.append(extra)
    friday_deviations = []
    if school.preferred_friday_hours is not None:
        for classroom in classrooms(school):
            indices = [i for i, lesson in enumerate(school.lessons) if lesson.classroom == classroom]
            total = sum(x[i, slot] for i in indices for slot in range(4 * school.periods, 5 * school.periods))
            deviation = model.new_int_var(0, school.periods, 'friday_deviation')
            model.add_abs_equality(deviation, total - school.preferred_friday_hours)
            friday_deviations.append(deviation)
    # A unit of Friday deviation outweighs every possible subject-distribution penalty.
    model.minimize((sum(l.hours for l in school.lessons) + 1) * sum(friday_deviations) + sum(penalties))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = school.time_limit
    solver.parameters.num_search_workers = 2
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {'status': 'infeasible' if status == cp_model.INFEASIBLE else 'unknown', 'entries': [], 'issues': ['Kufizimet janë të papajtueshme. Çdo klasë duhet ta nisë nga ora e parë, pa orë të zbrazëta; kontrollo edhe disponueshmërinë e profesorëve për orët e para.' if status == cp_model.INFEASIBLE else 'Koha përfundoi pa gjetur zgjidhje; pamundësia nuk është provuar.']}
    entries = [{'lesson': i, 'slot': s} for i in range(len(school.lessons)) for s in slots if solver.value(x[i,s])]
    errors = verify(school, entries)
    if errors: raise RuntimeError('Independent verification failed: '+str(errors))
    return {'status': 'optimal' if status == cp_model.OPTIMAL else 'feasible', 'entries': entries, 'issues': [], 'penalty': sum(solver.value(p) for p in penalties), 'friday_deviation': sum(solver.value(p) for p in friday_deviations), 'friday_loads': {c: sum(school.lessons[e['lesson']].classroom == c and e['slot'] // school.periods == 4 for e in entries) for c in sorted(classrooms(school))} if school.preferred_friday_hours is not None else {}, 'seconds': solver.wall_time, 'verified': True}

app = FastAPI(title='Orari.ai')

@app.post('/api/generate')
def schedule(school: School):
    return generate(school)

@app.get('/api/health')
def health():
    return {'status': 'ok'}

class ScheduleEntry(BaseModel):
    lesson: int = Field(ge=0)
    slot: int = Field(ge=0)

class ExportRequest(BaseModel):
    school: School
    entries: list[ScheduleEntry] = Field(min_length=1, max_length=1200)
    classes: list[str] = Field(default_factory=list, max_length=250)
    school_name: str = Field(default='', max_length=200)
    title: str = Field(default='', max_length=200)
    mode: Literal['all', 'classroom', 'teacher', 'room'] = 'all'
    content: Literal['teacher', 'subject', 'both'] = 'teacher'
    value: str = Field(default='', max_length=80)

    @model_validator(mode='after')
    def class_names(self):
        if any(not name or len(name) > 80 for name in self.classes):
            raise ValueError('Emër klase i pavlefshëm.')
        return self

@app.get('/api/examples/photo')
def example_photo():
    from app.examples import photo_example
    example = photo_example()
    source = example['state']
    school = School(**{**source, 'teachers': [Teacher(name=t['name']) for t in source['teachers']]})
    errors = verify(school, example['entries'])
    if errors:
        raise RuntimeError('Photo transcription must pass verification: ' + str(errors))
    return {**example, 'verified': True}

@app.post('/api/export/{format}')
def export_schedule(format: Literal['xlsx', 'docx', 'pdf'], request: ExportRequest):
    from app.exports import document_bytes
    errors = verify(request.school, [e.model_dump() for e in request.entries])
    if errors:
        raise HTTPException(status_code=422, detail='Orari nuk është i vlefshëm: ' + ' '.join(errors))
    try:
        content = document_bytes(request, format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    mime = {'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'pdf': 'application/pdf'}
    return Response(content, media_type=mime[format], headers={'Content-Disposition': f'attachment; filename="orari-javor.{format}"'})

app.mount('/', StaticFiles(directory=Path(__file__).parent / 'static', html=True), name='web')
