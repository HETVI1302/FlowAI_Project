from django.shortcuts import render


def landing_page(request):
    """
    Public marketing home page: nav, hero, animated stats, features, about,
    services, smart-city section, contact, footer. Stats shown here are
    static placeholders — the live WebSocket-driven numbers ship with the
    Dashboard module in the next phase.
    """
    context = {
        'stats': [
            {'label': 'Intersections Monitored', 'value': 24, 'suffix': '+'},
            {'label': 'Vehicles Tracked Today', 'value': 18400, 'suffix': '+'},
            {'label': 'Avg. Wait Time Reduced', 'value': 32, 'suffix': '%'},
            {'label': 'CO₂ Emissions Cut', 'value': 19, 'suffix': '%'},
        ],
    }
    return render(request, 'home/index.html', context)
