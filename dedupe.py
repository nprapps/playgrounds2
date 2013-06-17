import data

possible_dupes = [
    'Adventure Playground',
    'Asser Levy Playground',
    'Belmont Playground',
    'Bowne Playground',
    'Brower Park',
    'Fox Playground',
    'Harlem River Park',
    'Jackie Robinson Park',
    'Midland Playground',
    'Morningside Park',
    'Morningside Playground',
    'Nautilus Playground',
    'Owls Head Park',
    'Playground',
    'Playground For All Children',
    'Washington Park',
    'Wolfes Pond Park'
]

for dupe in possible_dupes:
    d = data.Playground.select().where(data.Playground.name == dupe)
    print dupe
    for playground in d:
        print '\t%s (lat%s lon%s)' % (playground.city, playground.latitude, playground.longitude)
