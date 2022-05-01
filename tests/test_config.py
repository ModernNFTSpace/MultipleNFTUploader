from config import search_mismatches, check_filenames_conflict

"""
run <config.py> for detailed output
>python config.py -h
"""

def test_search_mismatches():
    assert len([e for errors in search_mismatches().values() for e in errors]) == 0

def test_check_filenames_conflict():
    assert len(check_filenames_conflict()) == 0