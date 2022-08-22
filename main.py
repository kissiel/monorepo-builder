"""
git-filter-repo is directly taken from the upstream repo,
commit d760d24cf74a0ee68134d4b83a43d1e8ea3b6e1c
The upstream license as of time of that commit is MIT
"""

import random
import os
import shutil
import string
import subprocess
import tempfile

from functools import partial
from multiprocessing import Pool, cpu_count

from git_filter_repo import FilteringOptions, RepoFilter



# the repos to be merged into monorepo are defined as a triple that contains:
# TARGET_SUBDIR_NAME, ORIGINAL_REPO_URI, BRANCH_TO_BE_USED_FROM_ORIGINAL_REPO

REPOS = [
    ('metabox', '/home/kissiel/mono-repos/metabox', 'main'),
    ('checkbox-ng', '/home/kissiel/mono-repos/checkbox-ng', 'master'),
    ('checkbox-support', '/home/kissiel/mono-repos/checkbox-support', 'master'),
    ('plainbox-provider-checkbox', '/home/kissiel/mono-repos/plainbox-provider-checkbox', 'master'),
    ('plainbox-provider-resource', '/home/kissiel/mono-repos/plainbox-provider-resource', 'master'),
]

TARGET_REPO = '/home/kissiel/checkbox'

run = partial(subprocess.run, shell=True)

def filter_branch_to_subdir(subdir, path):
    args = [
        '--source', path,
        '--target', path,
        '--to-subdirectory-filter', subdir,
    ]
    RepoFilter(FilteringOptions.parse_args(args)).run()

def main():

    if os.path.exists(TARGET_REPO):
        raise SystemExit(f"{TARGET_REPO} already exists!")

    # TODO: assert that the config makes sense

    # initiate the target repository
    print(f"Creating target repository {TARGET_REPO}")
    run(f"git init --initial-branch main {TARGET_REPO}")

    # prepare temporary storages for the source repos
    # one tempdir is enough, all repos will be cloned as subdirs of the tmpdir
    with tempfile.TemporaryDirectory() as tmp_dir:
        print(f"{tmp_dir} created for the filter-branch operations")
        intermediate_dirs = []  # each dir is a pair: (subdir, path)
        for target, source, branch in REPOS:
            target_dir = os.path.join(tmp_dir, target)
            print(f"Cloning {source} into {target_dir}")
            run(f"git clone {source} {target_dir}")
            print(f"Moving all of the files to their respective subdirs")
            # let's remember the target dir as an arg for the next parallel bit 
            intermediate_dirs.append((target, target_dir, ))
            # we need to rebake the args for each call to filter_branch so it's
            # easier to follow
        print("Running git filter-branch in parallel on all source repos")
        with Pool(processes=cpu_count()) as pool:
            results = pool.starmap(filter_branch_to_subdir, intermediate_dirs)
        os.chdir(TARGET_REPO)
        for target, source, branch in REPOS:
            target_dir = os.path.join(tmp_dir, target)
            run(f"git remote add {target} {target_dir}")
            run(f"git fetch {target}")
            merge_opts = "--allow-unrelated-histories --no-edit"
            run(f"git merge {merge_opts} {target}/{branch}")
            run(f"git remote rm {target}")
        print(f"{target_dir}")

    
if __name__ == '__main__':
    main()
