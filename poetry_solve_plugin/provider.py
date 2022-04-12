"""Provider class that can handle duplicate packages in the dependency.

The implementation is copied from [radoering/poetry/puzzle/provider.py](https://github.com/radoering/poetry/blob/bafff7d9693513f3ec5b3789a4f31cd02aecf832/src/poetry/puzzle/provider.py).

"""  # noqa: E501

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from poetry.core.semver.empty_constraint import EmptyConstraint
from poetry.core.version.markers import AnyMarker
from poetry.core.version.markers import MarkerUnion

from poetry.packages import DependencyPackage
from poetry.puzzle.exceptions import OverrideNeeded
from poetry.puzzle.provider import Provider as BaseProvider


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.package import Package

    from poetry.repositories import Pool
    from poetry.utils.env import Env


logger = logging.getLogger(__name__)


class Provider(BaseProvider):

    UNSAFE_PACKAGES: set[str] = set()

    def __init__(
        self, package: Package, pool: Pool, io: Any, env: Env | None = None
    ) -> None:
        self._package = package
        self._pool = pool
        self._io = io
        self._env = env
        self._python_constraint = package.python_constraint
        self._search_for: dict[Dependency, list[Package]] = {}
        self._is_debugging = self._io.is_debug() or self._io.is_very_verbose()
        self._in_progress = False
        self._overrides: dict[DependencyPackage, dict[str, Dependency]] = {}
        self._deferred_cache: dict[Dependency, Package] = {}
        self._load_deferred = True

    def _get_dependencies_with_overrides(
        self, dependencies: list[Dependency], package: DependencyPackage
    ) -> list[Dependency]:
        overrides = self._overrides.get(package, {})
        _dependencies = []
        overridden = []
        for dep in dependencies:
            if dep.name in overrides:
                if dep.name in overridden:
                    continue

                # empty constraint is used in overrides to mark that the package has
                # already been handled and is not required for the attached markers
                if not overrides[dep.name].constraint.is_empty():
                    _dependencies.append(overrides[dep.name])
                overridden.append(dep.name)

                continue

            _dependencies.append(dep)
        return _dependencies

    def complete_package(self, package: DependencyPackage) -> DependencyPackage:
        if package.is_root():
            package = package.clone()
            requires = package.all_requires
        elif not package.is_root() and package.source_type not in {
            "directory",
            "file",
            "url",
            "git",
        }:
            package = DependencyPackage(
                package.dependency,
                self._pool.package(
                    package.name,
                    package.version.text,
                    extras=list(package.dependency.extras),
                    repository=package.dependency.source_name,
                ),
            )
            requires = package.requires
        else:
            requires = package.requires

        if self._load_deferred:
            # Retrieving constraints for deferred dependencies
            for r in requires:
                if r.is_directory():
                    self.search_for_directory(r)
                elif r.is_file():
                    self.search_for_file(r)
                elif r.is_vcs():
                    self.search_for_vcs(r)
                elif r.is_url():
                    self.search_for_url(r)

        optional_dependencies = []
        _dependencies = []

        # If some extras/features were required, we need to
        # add a special dependency representing the base package
        # to the current package
        if package.dependency.extras:
            for extra in package.dependency.extras:
                if extra not in package.extras:
                    continue

                optional_dependencies += [d.name for d in package.extras[extra]]

            package = package.with_features(list(package.dependency.extras))
            _dependencies.append(package.without_features().to_dependency())

        for dep in requires:
            if not self._python_constraint.allows_any(dep.python_constraint):
                continue

            if dep.name in self.UNSAFE_PACKAGES:
                continue

            if self._env and not dep.marker.validate(self._env.marker_env):
                continue

            if not package.is_root() and (
                (dep.is_optional() and dep.name not in optional_dependencies)
                or (
                    dep.in_extras
                    and not set(dep.in_extras).intersection(package.dependency.extras)
                )
            ):
                continue

            _dependencies.append(dep)

        dependencies = self._get_dependencies_with_overrides(_dependencies, package)

        # Searching for duplicate dependencies
        #
        # If the duplicate dependencies have the same constraint,
        # the requirements will be merged.
        #
        # For instance:
        #   - enum34; python_version=="2.7"
        #   - enum34; python_version=="3.3"
        #
        # will become:
        #   - enum34; python_version=="2.7" or python_version=="3.3"
        #
        # If the duplicate dependencies have different constraints
        # we have to split the dependency graph.
        #
        # An example of this is:
        #   - pypiwin32 (220); sys_platform == "win32" and python_version >= "3.6"
        #   - pypiwin32 (219); sys_platform == "win32" and python_version < "3.6"
        duplicates: dict[str, list[Dependency]] = {}
        for dep in dependencies:
            if dep.complete_name not in duplicates:
                duplicates[dep.complete_name] = []

            duplicates[dep.complete_name].append(dep)

        dependencies = []
        for dep_name, deps in duplicates.items():
            if len(deps) == 1:
                dependencies.append(deps[0])
                continue

            self.debug(f"<debug>Duplicate dependencies for {dep_name}</debug>")

            # Regrouping by constraint
            by_constraint: dict[str, list[Dependency]] = {}
            for dep in deps:
                if dep.constraint not in by_constraint:
                    by_constraint[dep.constraint] = []

                by_constraint[dep.constraint].append(dep)

            # We merge by constraint
            for constraint, _deps in by_constraint.items():
                new_markers = []
                for dep in _deps:
                    marker = dep.marker.without_extras()
                    if marker.is_any():
                        # No marker or only extras
                        continue

                    new_markers.append(marker)

                if not new_markers:
                    continue

                dep = _deps[0]
                dep.marker = dep.marker.union(MarkerUnion(*new_markers))
                by_constraint[constraint] = [dep]

                continue

            if len(by_constraint) == 1:
                self.debug(f"<debug>Merging requirements for {deps[0]!s}</debug>")
                dependencies.append(list(by_constraint.values())[0][0])
                continue

            # We leave dependencies as-is if they have the same
            # python/platform constraints.
            # That way the resolver will pickup the conflict
            # and display a proper error.
            _deps = [value[0] for value in by_constraint.values()]
            seen = set()
            for _dep in _deps:
                pep_508_dep = _dep.to_pep_508(False)
                if ";" not in pep_508_dep:
                    _requirements = ""
                else:
                    _requirements = pep_508_dep.split(";")[1].strip()

                if _requirements not in seen:
                    seen.add(_requirements)

            if len(_deps) != len(seen):
                for _dep in _deps:
                    dependencies.append(_dep)

                continue

            # At this point, we raise an exception that will
            # tell the solver to make new resolutions with specific overrides.
            #
            # For instance, if the foo (1.2.3) package has the following dependencies:
            #   - bar (>=2.0) ; python_version >= "3.6"
            #   - bar (<2.0) ; python_version < "3.6"
            #
            # then the solver will need to make two new resolutions
            # with the following overrides:
            #   - {<Package foo (1.2.3): {"bar": <Dependency bar (>=2.0)>}
            #   - {<Package foo (1.2.3): {"bar": <Dependency bar (<2.0)>}
            _deps = [_dep[0] for _dep in by_constraint.values()]

            def fmt_warning(d: Dependency) -> str:
                marker = d.marker if not d.marker.is_any() else "*"
                return (
                    f"<c1>{d.name}</c1> <fg=default>(<c2>{d.pretty_constraint}</c2>)</>"
                    f" with markers <b>{marker}</b>"
                )

            warnings = ", ".join(fmt_warning(d) for d in _deps[:-1])
            warnings += f" and {fmt_warning(_deps[-1])}"
            self.debug(
                f"<warning>Different requirements found for {warnings}.</warning>"
            )

            # We need to check if one of the duplicate dependencies
            # has no markers. If there is one, we need to change its
            # environment markers to the inverse of the union of the
            # other dependencies markers.
            # For instance, if we have the following dependencies:
            #   - ipython
            #   - ipython (1.2.4) ; implementation_name == "pypy"
            #
            # the marker for `ipython` will become `implementation_name != "pypy"`.
            #
            # Further, we have to merge the constraints of the requirements
            # without markers into the constraints of the requirements with markers.
            # for instance, if we have the following dependencies:
            #   - foo (>= 1.2)
            #   - foo (!= 1.2.1) ; python == 3.10
            #
            # the constraint for the second entry will become (!= 1.2.1, >= 1.2)
            any_markers_dependencies = [d for d in _deps if d.marker.is_any()]
            other_markers_dependencies = [d for d in _deps if not d.marker.is_any()]

            marker = other_markers_dependencies[0].marker
            for other_dep in other_markers_dependencies[1:]:
                marker = marker.union(other_dep.marker)
            inverted_marker = marker.invert()

            if any_markers_dependencies:
                for dep_any in any_markers_dependencies:
                    dep_any.marker = inverted_marker
                    for dep_other in other_markers_dependencies:
                        dep_other.set_constraint(
                            dep_other.constraint.intersect(dep_any.constraint)
                        )
            elif not inverted_marker.is_empty():
                # if there is no any marker dependency
                # and the inverted marker is not empty,
                # a dependency with the inverted union of all markers is required
                # in order to not miss other dependencies later, for instance:
                #   - foo (1.0) ; python == 3.7
                #   - foo (2.0) ; python == 3.8
                #   - bar (2.0) ; python == 3.8
                #   - bar (3.0) ; python == 3.9
                #
                # the last dependency would be missed without this,
                # because the intersection with both foo dependencies is empty
                inverted_marker_dep = _deps[0].with_constraint(EmptyConstraint())
                inverted_marker_dep.marker = inverted_marker
                _deps.append(inverted_marker_dep)

            overrides = []
            overrides_marker_intersection = AnyMarker()
            for dep_overrides in self._overrides.values():
                for _dep in dep_overrides.values():
                    overrides_marker_intersection = (
                        overrides_marker_intersection.intersect(_dep.marker)
                    )
            for _dep in _deps:
                if not overrides_marker_intersection.intersect(_dep.marker).is_empty():
                    current_overrides = self._overrides.copy()
                    package_overrides = current_overrides.get(package, {}).copy()
                    package_overrides.update({_dep.name: _dep})
                    current_overrides.update({package: package_overrides})
                    overrides.append(current_overrides)

            if overrides:
                raise OverrideNeeded(*overrides)

        # Modifying dependencies as needed
        clean_dependencies = []
        for dep in dependencies:
            if not package.dependency.transitive_marker.without_extras().is_any():
                marker_intersection = (
                    package.dependency.transitive_marker.without_extras().intersect(
                        dep.marker.without_extras()
                    )
                )
                if marker_intersection.is_empty():
                    # The dependency is not needed, since the markers specified
                    # for the current package selection are not compatible with
                    # the markers for the current dependency, so we skip it
                    continue

                dep.transitive_marker = marker_intersection

            if not package.dependency.python_constraint.is_any():
                python_constraint_intersection = dep.python_constraint.intersect(
                    package.dependency.python_constraint
                )
                if python_constraint_intersection.is_empty():
                    # This dependency is not needed under current python constraint.
                    continue
                dep.transitive_python_versions = str(python_constraint_intersection)

            clean_dependencies.append(dep)

        package = DependencyPackage(
            package.dependency, package.with_dependency_groups([], only=True)
        )

        for dep in clean_dependencies:
            package.add_dependency(dep)

        return package
