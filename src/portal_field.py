"""The twenty confirmed labels and their fixed source-roster identities."""

PORTAL_PLAYERS = {
    'Rashid Khan': 4722,
    'Abdul Samad': 7446,
    'Haider Ali': 7338,
    'Basil Hameed': 8638,
    'Muhammad Farooq': 27373,
    'Bashir Ahmad': 29833,
    'Mahendra Singh Dhoni': 8,
    'Piyush Chawla': 23,
    'Ishant Sharma': 28,
    'Nathan Bracken': 35,
    'Virat Kohli': 47,
    'Faf du Plessis': 88,
    'Wriddhiman Saha': 109,
    'Rohit Sharma': 126,
    'Shikhar Dhawan': 142,
    'Dinesh Karthik': 143,
    'Pradeep Sangwan': 147,
    'Ravindra Jadeja': 152,
    'Amit Mishra': 158,
    'Dwayne Bravo': 161,
}


def portal_players(role):
    players = PORTAL_PLAYERS.copy()
    if role == 'bowlers':
        players['Haider Ali'] = 28756  # UAE bowler, distinct from the Pakistan batter.
    return players
