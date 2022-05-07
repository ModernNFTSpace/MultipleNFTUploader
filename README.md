<div align="center">

# Modern NFT Uploader

![opensea-io-badge]
![assets-up-yo-badge]
![speed-badge]
![mnu-version-badge]
[![License][license-badge]][license]

**MNU** created to help with uploading multiple assets to [opensea.io](https://opensea.io) 🚢

<br/>Minimum uploading speed → _1000 assets per hour_⁽¹⁾

![Image][under-title-image]

[Futures](#-features) •
[Installation](#-installation) •
[Support](#support) 
</div>

¹ Tested on 2000 assets ~100 KB and ~3 sec for each<br />
¹ Assets per Hour → <a name="aph">ApH</a>

####Note
>MNU only uploads assets, to put up for sale use [MNManager](#mnm-repo)(repo will be unlocked soon)
>For view full pipeline of uploading/selling assets read \[[How upload multiple assets to opensea.io](#mn-guide-repo)\]
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
  - [Setup configs]()
  - [Prepare assets]()
  - [Testing]()
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
###Install Google Chrome
>⚠ If it is already installed on your system, skip this step.

1. Follow steps described at [Google Support](https://support.google.com/chrome/answer/95346)
### Install python
1. [Download](https://www.python.org/downloads/) installer for your OS
2. Run it and follow the instructions
### Install MNU
1. Create a folder and go into it
    + CMD
        ```sh
        mkdir "%programfiles%\MNSpace" && cd "%programfiles%\MNSpace"
        ```
    + Bash
        ```sh
        mkdir /home/MNSpace && cd "$_"
        ```
1. Clone repository and go into MNU dir:
    ```sh
    git clone https://github.com/ModernNFTSpace/MultipleNFTUploader.git && cd MultipleNFTUploader
    ```
1. Install requirements:
    ```sh
    pip install -r requirements.txt
    ```
1. Generate empty configs; Download and patch webdriver:
    ```sh
    python main.py --setup
    ```
## 💡 Getting started
>Note: At the moment, MNU does not have the most user-friendly interface (will be fixed during refactoring). This is due to the emphasis on quality and speed of work.
## 🌟 Features
* 1000 [ApH](#aph)
* Almost complete emulation of human behavior
* Support for all types accepted by the opensea.io(image/\*,video/\*,audio/\*,webgl/\*,.glb,.gltf)
* Fault resistance pipeline. In case of failure, the resource will not be lost, but will be re-queued. Also you can stop the process at any time and continue from the same place later
* The UI is implemented using HTTP, so it is possible to implement GUI as a web interface(Webhooks and long poling supported)
## Support
## Contacts

If you have any questions or suggestions please contact us:
 - via [telegram bot](#tg-feedback-bot-link)
 
## License
## 🔗 Links

[mn-guide-repo]: #
[mnm-repo]: #
[tg-feedback-bot-link]: https://t.me/mns_feedback_bot
[under-title-image]: ../master/docs/contrib/under_title.png?raw=true
[assets-up-yo-badge]: https://img.shields.io/badge/assets%20up%20to-100mb-green
[mnu-version-badge]: https://img.shields.io/github/v/release/ModernNFTSpace/MultipleNFTUploader?include_prereleases
[speed-badge]: https://img.shields.io/badge/speed-1000ApH-green
[opensea-io-badge]: https://img.shields.io/badge/opensea.io-supported-brightgreen?logo=opensea
[license-badge]: https://img.shields.io/github/license/ModernNFTSpace/MultipleNFTUploader
[license]: ../blob/master/LICENSE