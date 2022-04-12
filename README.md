# poetry-solve-plugin

[![Test](https://img.shields.io/github/workflow/status/KaoruNishikawa/poetry-solve-plugin/Test?logo=github&label=Test&style=flat-square)](https://github.com/KaoruNishikawa/poetry-solve-plugin/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?label=License&style=flat-square)](LICENSE)

Poetry plug-in that temporary resolves issue on complicated version constraints handling.

## Features

This library provides:

- something.

Once after [poetry/\#4695](https://github.com/python-poetry/poetry/issues/4695) is closed, this plug-in won't be maintained any longer.

## Acknowledgments

The implementations are copies of the following scripts. The purpose of this repository
is to provide the means of early-accessing to the features under development.

- [radoering/poetry/puzzle/provider.py](https://github.com/radoering/poetry/blob/bafff7d9693513f3ec5b3789a4f31cd02aecf832/src/poetry/puzzle/provider.py)

## Usage

1. Check the Poetry version.

    ```shell
    $ poetry --version
    Poetry version 1.2.0b1
    ```

    - If the version is `1.1.*`, update to `1.2.*` using the following command.

        ```shell
        poetry self update 1.2.0b1
        ```

    - If Poetry isn't installed, run the following command.

        ```shell
        curl -sSL https://install.python-poetry.org | python3 - --version 1.2.0b1
        ```

2. Install the plug-in.

    ```shell
    poetry plugin add git+https://github.com/KaoruNishikawa/poetry-solve-plugin.git
    ```

---

This library is using [Semantic Versioning](https://semver.org).
