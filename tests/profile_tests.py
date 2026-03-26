import cProfile
import pstats
import pytest
import sys

# Define the output file for the profile data
PROFILE_FILE = "test_profile.prof"

# Use cProfile to run pytest.main()
with cProfile.Profile() as pr:
    # You can pass specific test arguments to pytest.main() if needed
    # e.g., ['tests/your_test_file.py']
    pytest.main(sys.argv[1:])

# Create a pstats object to process and save the stats
stats = pstats.Stats(pr)
stats.sort_stats(pstats.SortKey.CUMULATIVE) # Sort by cumulative time
stats.dump_stats(PROFILE_FILE) # Save to a file
