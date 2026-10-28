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

class School(BaseModel):
    days: int = Field(default=5, ge=1, le=7)
    periods: int = Field(default=6, ge=1, le=12)
    teachers: list[Teacher] = Field(min_length=1, max_length=100)
    lessons: list[Lesson] = Field(min_length=1, max_length=250)
    time_limit: float = Field(default=10, ge=1, le=30)

    @model_validator(mode='after')
    def references(self):
        names = [t.name for t in self.teachers]
        if len(set(names)) != len(names):
            raise ValueError('Emrat e profesorëve duhet të jenë unikë.')
        if any(l.teacher not in names for l in self.lessons):
            raise ValueError('Çdo angazhim duhet të ketë profesor të regjistruar.')
        if any(s < 0 or s >= self.days*self.periods for t in self.teachers for s in t.unavailable):
            raise ValueError('Termini i padisponueshëm është jashtë javës.')
        if sum(l.hours for l in self.lessons) > 1200:
            raise ValueError('Versioni fillestar përkrah deri në 1200 orë.')
        return self

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
    for classroom in {lesson.classroom for lesson in school.lessons}:
        for day in range(school.days):
            periods = [p for p in range(school.periods) if ('class', classroom, day * school.periods + p) in occupied]
            if periods and periods != list(range(periods[-1] + 1)):
                errors.append(f'{classroom}, dita {day + 1}: mësimi duhet të nisë në orën e parë dhe të vazhdojë pa orë të zbrazëta.')
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
    if issues: return {'status': 'infeasible', 'issues': issues, 'entries': []}
    model = cp_model.CpModel()
    x = {(i, s): model.new_bool_var(f'x_{i}_{s}') for i in range(len(school.lessons)) for s in slots}
    unavailable = {t.name: set(t.unavailable) for t in school.teachers}
    for i, lesson in enumerate(school.lessons):
        model.add(sum(x[i, s] for s in slots) == lesson.hours)
        for s in unavailable[lesson.teacher]: model.add(x[i, s] == 0)
    for kind in ('classroom', 'teacher', 'room'):
        for value in {getattr(l, kind) for l in school.lessons} - {''}:
            indices = [i for i, l in enumerate(school.lessons) if getattr(l, kind) == value]
            for s in slots: model.add(sum(x[i, s] for i in indices) <= 1)
    # Class occupancy is a daily prefix: 1,1,...,1,0,...,0.
    # This prohibits both late starts and internal holes; teachers may still arrive later.
    for classroom in {lesson.classroom for lesson in school.lessons}:
        indices = [i for i, lesson in enumerate(school.lessons) if lesson.classroom == classroom]
        for day in range(school.days):
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
            extra = model.new_int_var(0, school.periods, 'repeated_subject')
            model.add(extra >= sum(x[i,s] for i in indices for s in range(d*school.periods,(d+1)*school.periods))-1)
            penalties.append(extra)
    model.minimize(sum(penalties))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = school.time_limit
    solver.parameters.num_search_workers = 2
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {'status': 'infeasible' if status == cp_model.INFEASIBLE else 'unknown', 'entries': [], 'issues': ['Kufizimet janë të papajtueshme. Çdo klasë duhet ta nisë nga ora e parë, pa orë të zbrazëta; kontrollo edhe disponueshmërinë e profesorëve për orët e para.' if status == cp_model.INFEASIBLE else 'Koha përfundoi pa gjetur zgjidhje; pamundësia nuk është provuar.']}
    entries = [{'lesson': i, 'slot': s} for i in range(len(school.lessons)) for s in slots if solver.value(x[i,s])]
    errors = verify(school, entries)
    if errors: raise RuntimeError('Independent verification failed: '+str(errors))
    return {'status': 'optimal' if status == cp_model.OPTIMAL else 'feasible', 'entries': entries, 'issues': [], 'penalty': int(solver.objective_value), 'seconds': solver.wall_time, 'verified': True}

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
