#!/usr/bin/env python3

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
import sys
import tempfile

from functools import partial
from multiprocessing import Pool, cpu_count

from git_filter_repo import FilteringOptions, RepoFilter


# the repos to be merged into monorepo are defined as a triple that contains:
# TARGET_SUBDIR_NAME, ORIGINAL_REPO_URI, BRANCH_TO_BE_USED_FROM_ORIGINAL_REPO

REPOS = [
    (    
        "metabox",
        "https://git.launchpad.net/~checkbox-dev/checkbox/+git/metabox",
        "main"
    ),
    (   
        "checkbox-ng",
        "https://git.launchpad.net/checkbox-ng",
        "master"
    ),
    (
        "checkbox-ng-packaging",
        "https://git.launchpad.net/~checkbox-dev/checkbox-ng/+git/packaging",
        "master",
    ),
    (
        "checkbox-support-packaging",
        "https://git.launchpad.net/~checkbox-dev/checkbox-support/+git/packaging",
        "master",
    ),
    (
        "checkbox-support",
        "https://git.launchpad.net/checkbox-support",
        "master",
    ),
    (
        "providers/base-packaging",
        "https://git.launchpad.net/~checkbox-dev/plainbox-provider-checkbox/+git/packaging",
        "master",
    ),
    (
        "providers/base",
        "https://git.launchpad.net/plainbox-provider-checkbox",
        "master",
    ),
    (
        "providers/resource-packaging",
        "https://git.launchpad.net/~checkbox-dev/plainbox-provider-resource/+git/packaging",
        "master",
    ),
    (
        "providers/resource",
        "https://git.launchpad.net/plainbox-provider-resource",
        "master",
    ),
    (
        "providers/tpm2-packaging",
        "https://git.launchpad.net/~checkbox-dev/plainbox-provider-tpm2/+git/packaging",
        "master",
    ),
    (
        "providers/tpm2",
        "https://git.launchpad.net/plainbox-provider-tpm2",
        "master",
    ),
    (
        "providers/ipdt-packaging",
        "https://git.launchpad.net/~checkbox-dev/plainbox-provider-ipdt/+git/packaging",
        "master",
    ),
    (
        "providers/ipdt",
        "https://git.launchpad.net/plainbox-provider-ipdt",
        "master",
    ),
    (
        "providers/phoronix-packaging",
        "https://git.launchpad.net/~checkbox-dev/checkbox-provider-phoronix/+git/packaging",
        "master",
    ),
    (
        "providers/phoronix",
        "https://git.launchpad.net/checkbox-provider-phoronix",
        "master",
    ),
    (
        "providers/gpgpu-packaging",
        "https://git.launchpad.net/~checkbox-dev/checkbox-provider-gpgpu/+git/packaging",
        "master",
    ),
    (
        "providers/gpgpu",
        "https://git.launchpad.net/checkbox-provider-gpgpu",
        "master",
    ),
    (
        "providers/sru-packaging",
        "https://git.launchpad.net/~checkbox-dev/plainbox-provider-sru/+git/packaging",
        "master",
    ),
    (
        "providers/sru",
        "https://git.launchpad.net/plainbox-provider-sru",
        "master",
    ),
    (
        "providers/certification-client-packaging",
        "https://git.launchpad.net/~checkbox-dev/plainbox-provider-certification-client/+git/packaging",
        "master",
    ),
    (
        "providers/certification-client",
        "https://git.launchpad.net/plainbox-provider-certification-client",
        "master",
    ),
    (
        "providers/certification-server-packaging",
        "https://git.launchpad.net/~checkbox-dev/plainbox-provider-certification-server/+git/packaging",
        "master",
    ),
    (
        "providers/certification-server",
        "https://git.launchpad.net/plainbox-provider-certification-server",
        "master",
    ),
    (
        "providers/docker",
        "https://git.launchpad.net/plainbox-provider-docker",
        "master",
    ),
    (
        "providers/iiotg",
        "https://git.launchpad.net/checkbox-provider-iiotg",
        "master",
    ),
    (
        "providers/edgex",
        "https://git.launchpad.net/checkbox-provider-edgex",
        "master",
    ),
]

TARGET_REPO = "/home/sylvain/monorepo-staging"

run = partial(subprocess.run, shell=True)


def filter_branch_to_subdir(subdir, path):
    args = [
        "--source",
        path,
        "--target",
        path,
        "--to-subdirectory-filter",
        subdir.replace("-packaging", ""),
    ]
    if path.endswith('packaging'):
        args.extend(["--path", "debian"])
    RepoFilter(FilteringOptions.parse_args(args)).run()


def main():

    just_update = False
    if os.path.exists(TARGET_REPO):
        if len(sys.argv) == 2 and sys.argv[1] == '--update':
            just_update = True
        else:
            raise SystemExit(
                f"{TARGET_REPO} already exists! Use --update to update")

    # TODO: assert that the config makes sense

    if not just_update:
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
            run(f"git clone -b {branch} {source} {target_dir}")
            print(f"Moving all of the files to their respective subdirs")
            # let's remember the target dir as an arg for the next parallel bit
            intermediate_dirs.append(
                (
                    target,
                    target_dir,
                )
            )
            # we need to rebake the args for each call to filter_branch so it's
            # easier to follow
        print("Running git filter-branch in parallel on all source repos")
        with Pool(processes=cpu_count()) as pool:
            results = pool.starmap(filter_branch_to_subdir, intermediate_dirs)
        os.chdir(TARGET_REPO)
        for target, source, branch in REPOS:
            target_dir = os.path.join(tmp_dir, target)
            run(f"git remote add {target} {target_dir}")
            if just_update:
                pull_opts = '--no-tags --no-rebase --no-edit'
                outcome = run(f"git pull {pull_opts} {target} {branch}",
                    stdout=subprocess.PIPE)
                output = outcome.stdout.decode(sys.stdout.encoding)
                print(output)
                if 'Already up to date.' not in output:
                    # there was no merge, so the commit should not be amended
                    run(f"git commit --amend -m 'monorepo refresh: pull of {source}'")
            else:
                run(f"git fetch {target}")
                merge_opts = "--allow-unrelated-histories --no-edit"
                run(f"git merge {merge_opts} {target}/{branch}")
            run(f"git remote rm {target}")
        print(f"{target_dir}")


if __name__ == "__main__":
    main()
