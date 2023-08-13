# gf180 0.0.3

GlobalFoundries 180nm MCU based on [Google open source PDK](https://github.com/google/globalfoundries-pdk-libs-gf180mcu_fd_pr)

This is a pure python implementation of the PDK.

## Installation

### Installation for new python users

If you don't have python installed on your system you can [download the gdsfactory installer](https://github.com/gdsfactory/gdsfactory/releases) that includes python3, miniconda and all gdsfactory plugins.

### Installation for new gdsfactory users

If you already have python installed. Open Anaconda Prompt and then install the ubcpdk using pip.

![anaconda prompt](https://i.imgur.com/Fyal5sT.png)

```
pip install gf180 --upgrade
```

Then you need to restart Klayout to make sure the new technology installed appears.

### Installation for developers

For developers you need to `git clone` the GitHub repository, fork it, git add, git commit, git push and merge request your changes.

```
git clone https://github.com/gdsfactory/gf180.git
cd gf180
make install
```

## Documentation

- Run notebooks on [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/gdsfactory/binder-sandbox/HEAD)
- [gdsfactory docs](https://gdsfactory.github.io/gdsfactory/)
