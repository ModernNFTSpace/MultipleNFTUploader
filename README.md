<div align="center">

# Modern NFT Uploader

![opensea-io-badge]
![assets-up-yo-badge]
![speed-badge]
![mnu-version-badge]
[![License][license-badge]][license]

**MNU** created to help with uploading multiple assets to [opensea.io](https://opensea.io) 🚢

<br>Minimum uploading speed → _1000 assets per hour_⁽¹⁾

![Image][under-title-image]

[Futures](#-features) •
[Installation](#-installation) •
[Support](#support)
 
[![liberapay-badge]][liberapay-link]
![last-commit-date-badge]
[![patreon-badge]][patreon-link]
</div>

¹ Tested on 2000 assets ~100 KB and ~3 sec for each<br />
¹ Assets per Hour → <a name="aph">ApH</a>

#### Note
>MNU only uploads assets, to put up for sale use [MNManager](#mnm-repo)(repo will be unlocked soon)
>For view full pipeline of uploading/selling assets read \[[How upload multiple assets to opensea.io][mn-guide-repo]\]
><br><br>
>Project is currently in Alpha, but is actively developed. If you want support us go to this [section](#support)
><br><br>
>Project development depends not only on financial support, but also on your activity *(the main motivation for development)*
><br>
>So if you use **MNU** or have any questions while using it, [contact us](#contacts) and we will try to help

## Table of content
- [Futures](#-features)
- [Requirements](#requirements)
- [Installation](#-installation)
  - [Install package](#install-mnu)
- [Getting started](#-getting-started)
  - [Prepare assets](#prepare-assets)
  - [Setup configs](#setup-configs)
  - [Testing](#installation-testing)
- [Support](#support)
- [Contacts](#contacts)
- [License](#license)
- [Links](#-links)

## Requirements
Backend part:
>OS: Windows 7+ (UNIX support will be added)<br>
>Python 3.8+<br>
>Google Chrome<br>
>SSD(Optional)

GUI part(implemented example):
>OpenGL 2.0+
## 💾 Installation
### Install Google Chrome
>⚠ If it is already installed on your system, skip this step.

1. Follow steps described at [Google Support](https://support.google.com/chrome/answer/95346)
### Install python
1. [Download](https://www.python.org/downloads/) installer for your OS
2. Run it and follow the instructions
### Install MNU
1. Create a folder and go into it
    + CMD
        ```sh
        mkdir "%programfiles%\MNSpace" && cd /d "%programfiles%\MNSpace"
        ```
    + Bash
        ```sh
        mkdir /home/MNSpace && cd "$_"
        ```
1. Clone repository and go into MNU dir:
    ```sh
    git clone --recurse-submodules https://github.com/ModernNFTSpace/MultipleNFTUploader.git && cd MultipleNFTUploader
    ```
1. Install requirements:
    ```sh
    pip install -r requirements.txt
    ```
1. Generate empty configs; Download and patch webdriver:
    ```sh
    python main.py --setup
    ```
1. In "WebDriver info" section will be showing downloaded version of webdriver.
If it differs from the version(**major** part) of Google Chrome you have - read [How manually download webdriver][guide-manually-download-webdriver]
 
## 💡 Getting started
>Note: At the moment, MNU does not have the most user-friendly interface (will be fixed during refactoring). This is due to the emphasis on quality and speed of work.
### Prepare assets
To work with MNU, you need to collect data about your assets in a so-called manifest file. This simplifies the process of searching for assets, and also provides a mechanism for customizing the traits of assets when uploading.

To simple prepare the assets, do:
1. Create a folder and copy all assets you want upload
1. Copy absolute path to folder
1. Run(Replace **ABS_PATH** with path which you copied earlier):
   ```sh
   python -m mn_penpusher --path "ABS_PATH"
   ```
1. Preparing complete. Remember the path to the folder, it will be needed to be included in the [configuration file](#collection_dir_config)
>Note: If the project is in demand, the GUI for preparing assets will be added

### Setup configs
MNU stores some data in configuration files, such as collection data (will be migrated), server settings, and metamask wallet data
>Note: <br>    Don`t use your main wallet for uploading.<br>    Instead create a new wallet and give it upload access to the collection
><br><br>    If you are use a different authorization method on opensea,<br>    then you will also need to get a Metamask wallet
><br><br>    [How create Metamask wallet and configure collection][guide-create-metamask] for using with MNU

⚠️if you have any problems - [contact us](#contacts)

1. Configure `configs/metamask.conf`:<br>
   1. Open in any editor
   1. Replace "null" with your Metamask secret phrase
      ```yaml
      secret_phase: null
      ```
   1. Save & exit
   
1. Configure `configs/metamask.conf`:<br>
   1. Open in any editor
   1. Paste inside quotes collection slug, in which you want to upload assets.<br>For example `mnu-collection` is a slug for `https://opensea.io/collection/mnu-collection`
      ```yaml
      collection_name: 'mnu-collection'
      ```
   1. <a name="collection_dir_config">Paste inside quotes absolute path to directory with your assets<br>(folder from ["Prepare assets"](#prepare-assets) step, with manifest file).</a>
      ```yaml
      collection_dir_local_path: 'C:\\collection_dir'
      ```
   1. Paste inside quotes base name for assets. It will be used for generating names.<br>For example: "MNU asset#0", "MNU asset#1", ... 
      ```yaml
      single_asset_name: 'MNU Asset'
      ```
   1. These settings are enough to start the upload. You can learn more about asset data customization [here][guide-asset-data-customization].
   1. Save & exit

### Installation testing
Run command:
```sh
py.test tests
```
Will be checked configs and a test upload will be performed (into a test collection)<br><br>
If tests finished without error/fail(xfailed doesn't count) ➡ congrats you set up MNU<br>(with the current lack of usability - this is a feat)🥳

## 🌟 Features
* 1000 [ApH](#aph)
* Almost complete emulation of human behavior
* Support for all types accepted by the opensea.io(image/\*,video/\*,audio/\*,webgl/\*,.glb,.gltf)
* Fault resistance pipeline. In case of failure, the resource will not be lost, but will be re-queued. Also you can stop the process at any time and continue from the same place later
* The UI is implemented using HTTP, so it is possible to implement GUI as a web interface(Webhooks and long poling supported)

## Support

You can support us financially, even 0.50$ will be enough:<br>
[![liberapay-badge]][liberapay-link]
[![patreon-badge]][patreon-link]
<br>
<br>
But if you have a penchant for art - better help us with the graphic design of the project 😉

## Contacts

If you have any questions or suggestions please contact us:
 - via [telegram bot](#tg-feedback-bot-link)
 
## License

[Read full license text][license-file-link]

## 🔗 Links

[ChromeDriver download page](https://chromedriver.chromium.org/) 
<br>
[Selenium WebDriver](https://selenium-python.readthedocs.io/)
<br>
[Opensea.io](https://opensea.io/)
<br>
[Metamask](https://metamask.io/)

[guide-create-metamask]: ../master/docs/guides/create_metamask_and_give_access/
[guide-asset-data-customization]: ../master/docs/guides/asset_data_customization/
[guide-manually-download-webdriver]: ../master/docs/guides/manually_download_webdriver/

[license-file-link]: ../master/LICENSE?raw=true
[mn-guide-repo]: https://github.com/ModernNFTSpace/How-upload-multiple-NFTs-to-opensea.io
[mnm-repo]: https://github.com/ModernNFTSpace/MNManager
[tg-feedback-bot-link]: https://t.me/mns_feedback_bot
[under-title-image]: ../master/docs/contrib/under_title.png?raw=true

[last-commit-date-badge]: https://img.shields.io/github/last-commit/ModernNFTSpace/MultipleNFTUploader?color=green

[patreon-badge]: https://img.shields.io/endpoint.svg?url=https%3A%2F%2Fshieldsio-patreon.vercel.app%2Fapi%3Fusername%3DModernNFTSpace%26type%3Dpatrons&style=flat
[patreon-link]: https://patreon.com/ModernNFTSpace
[liberapay-badge]: https://img.shields.io/liberapay/patrons/ModernNFTSpace.svg?logo=liberapay
[liberapay-link]: https://liberapay.com/ModernNFTSpace
[assets-up-yo-badge]: https://img.shields.io/badge/assets%20up%20to-100mb-green
[mnu-version-badge]: https://img.shields.io/github/v/release/ModernNFTSpace/MultipleNFTUploader?include_prereleases
[speed-badge]: https://img.shields.io/badge/speed-1000ApH-green
[opensea-io-badge]: https://img.shields.io/badge/opensea.io-supported-brightgreen?logo=opensea
[license-badge]: https://img.shields.io/github/license/ModernNFTSpace/MultipleNFTUploader
[license]: ../blob/master/LICENSE