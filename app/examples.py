"""Photo transcription. Unknown subjects/teachers are explicit placeholders."""
import json
from pathlib import Path

def photo_example():
    source = json.loads((Path(__file__).parent / 'data/photo.json').read_text())
    lessons, entries, indices, names = [], [], {}, []
    for day, rows in enumerate(source['days']):
        for period, row in enumerate(rows):
            for classroom, label in zip(source['classes'], row):
                if label is None:
                    continue
                subject = 'Sociologji' if label == 'Sociologji' else 'Lëndë e papërcaktuar'
                teacher = f'Pa caktuar · {classroom}' if label == 'Sociologji' else label
                if teacher not in names:
                    names.append(teacher)
                key = classroom, subject, teacher
                if key not in indices:
                    indices[key] = len(lessons)
                    lessons.append(dict(classroom=classroom, subject=subject, teacher=teacher, hours=0, room=''))
                index = indices[key]
                lessons[index]['hours'] += 1
                entries.append(dict(lesson=index, slot=day * 7 + period))
    return {
        'state': dict(days=5, periods=7, preferredFriday=6, teachers=[dict(name=n, blocked=[], maxHours=None) for n in names],
                      classes=source['classes'], subjects=['Lëndë e papërcaktuar', 'Sociologji'], lessons=lessons,
                      schoolName=source['school_name'], scheduleTitle=source['title']),
        'entries': entries,
        'note': 'Transkriptim nga fotoja: lëndët që nuk shfaqen janë të papërcaktuara. “Pa caktuar” është vendmbajtës i veçantë për secilën klasë me Sociologji; zëvendësoje me profesorin real. Nuk janë supozuar kufij javorë apo ditë pune. Preferencë e shtuar: të premten 6 orë për secilën klasë, kur rregullat strikte e lejojnë.'
    }
