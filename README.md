# HMBot

HMBot is an LLM-based mobile application automation testing tool that supports intelligent application exploration and testing on Android and HarmonyOS devices. It can autonomously explore and achieve testing goals based on user-defined hardware types or provided test scripts.

## Features

- LLM-based intelligent GUI exploration
- Support for multiple operating systems: Android and HarmonyOS
- Hardware resource testing: audio, microphone, camera, keyboard, etc.
- Cross-app and cross-platform migration of test scripts
- Automatic generation of window transition graphs (WTG)

## Installation Requirements

### Dependencies

- Python 3.9
- LLM API key
- ADB tools for Android devices
- HDC tools for HarmonyOS devices

### Installation Steps

1. Clone the repository
```bash
git clone <repository-url>
cd hmbot
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Install ADB and HDC tools

#### Install ADB (Android Debug Bridge)

##### macOS
```bash
# Install using Homebrew
brew install android-platform-tools
```

##### Windows
1. Download [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)
2. Extract the downloaded zip file
3. Add the extracted folder path to the system environment variable PATH

##### Linux
```bash
# Ubuntu/Debian
sudo apt-get install android-tools-adb

# Fedora
sudo dnf install android-tools
```

#### Install HDC (HarmonyOS Device Connector)

1. Download [DevEco Studio](https://developer.harmonyos.com/cn/develop/deveco-studio/)
2. Install DevEco Studio, which will automatically install HDC tools
3. Alternatively, you can download the [HDC toolkit](https://developer.harmonyos.com/cn/develop/deveco-studio/#download_hdc) separately

#### Verify Installation
```bash
# Verify ADB installation
adb version

# Verify HDC installation
hdc version
```

4. Configure LLM Parameters

Create and edit the `.env` file in the project directory:
```bash
touch .env
```

Please copy the LLM configuration sample below to the `.env` file and modify it with your own API information:
```
BASE_URL="https://api.openai.com/v1"
MODEL="gpt-4-turbo"
API_KEY="YOUR_API_KEY"
```

## Usage

### List Connected Devices

```bash
# List all HarmonyOS devices
python run.py devices --os harmony

# List all Android devices
python run.py devices --os android
```

### Application Exploration

Use LLM for application exploration:

```bash
python run.py explore --os <operating_system> -p <app_path> -s <device_port> --testcase <script_path> | --hardware <hardware_kind> [options]
```

Parameter description:
- `--os`: **[Required]** Specify the operating system type (android or harmony)
- `-p, --app_path`: **[Required]** Specify the path to the APK or HAP file of the application
- `-s, --serial`: **[Required]** Specify the device port number
- `-m, --max_steps`: [Optional] Specify the maximum number of exploration steps, default is 20
- `-o, --output`: [Optional] Specify the output directory, default is "output/"

You must specify one of the following exploration types: **[Required]**
- `--testcase`: Specify test script file paths for exploration, multiple paths can be specified, e.g., `--testcase test1.py test2.py`
- `--hardware`: Specify hardware resources to test, multiple resources can be specified, e.g., `--hardware audio camera`

### Examples
1. Test the speaker functionality of a HarmonyOS application:
```bash
python run.py explore --os harmony -p path/to/app.hap -s 127.0.0.1:5555 --hardware audio
```

2. Explore audio and camera functionality of an Android application:
```bash
python run.py explore --os android -p path/to/app.apk -s emulator-5554 --hardware audio camera
```

3. Explore an Android application using test scripts:
```bash
python run.py explore --os android -p path/to/app.apk -s emulator-5554 --testcase path/to/test_script1.py path/to/test_script2.py
```

4. Specify maximum exploration steps and output directory:
```bash
python run.py explore --os android -p path/to/app.apk -s emulator-5554 --hardware audio -m 30 -o results/
```

## Output Results

After exploration is complete, the results will be saved in the specified output directory, including:
- Window Transition Graph (WTG): Records the UI states and transitions of the application
- Screenshots: Screenshots of each UI state
- UI Widget Tree: Widget tree of each UI state