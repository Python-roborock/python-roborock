# Q10 VacuumTrait Test Scripts

This directory contains test scripts for the Q10 VacuumTrait functionality added in [PR #754](https://github.com/Python-roborock/python-roborock/pull/754).

## Scripts

### test_q10_simple.py
Interactive test script with detailed debug information. This script:
- Shows comprehensive device information
- Lists all available property APIs
- Provides an interactive menu to test vacuum commands
- Includes error handling and detailed output

**Use this script when:**
- You want to verify your device supports Q10 properties
- You need to debug connection or API issues
- You want detailed information about what's happening

### test_q10_vacuum.py
Basic test script for Q10 vacuum commands. A simpler version focused on testing the vacuum trait.

### test_q10_advanced.py (NEW!)
Advanced test suite with complex features and detailed diagnostics:
- Tests multiple cleaning modes (standard, area, fast map)
- Device status monitoring and diagnostics
- Structured test suite with multiple test categories
- Interactive menu for manual command testing
- Full test suite execution

**Use this script when:**
- You want to test advanced cleaning modes
- You need comprehensive diagnostics
- You want to verify all VacuumTrait features
- You're developing or debugging Q10 device support

## Usage

### Quick Start

1. Install the package in development mode:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

2. Run a test script:
```bash
# Simple script with debugging
python examples/Q10/test_q10_simple.py

# Basic script (minimal output)
python examples/Q10/test_q10_vacuum.py

# Advanced script with diagnostics
python examples/Q10/test_q10_advanced.py
```

3. On first run, you'll be prompted to log in:
   - Enter your Roborock account email
   - A code will be sent to your email
   - Enter the code to complete authentication
   - Credentials are cached for future runs in `~/.cache/roborock-user-params.pkl`

### What Each Script Does

#### test_q10_simple.py
```bash
$ python examples/Q10/test_q10_simple.py
📱 Found 1 device(s)
Device 1: Roborock Q10 S5+
✅ Using device: Roborock Q10 S5+
✅ Device has Q10 properties!
✅ Vacuum trait found: <roborock.devices.traits.b01.q10.vacuum.VacuumTrait ...>
```
- Best for: Verifying device setup and API availability
- Features: Full device diagnostics and comprehensive menu

#### test_q10_vacuum.py
```bash
$ python examples/Q10/test_q10_vacuum.py
📱 Found 1 device(s)
1. Roborock Q10 S5+ (roborock.vacuum.ss07)
✅ Using device: Roborock Q10 S5+
```
- Best for: Quick testing and command execution
- Features: Minimal output, clean interface

#### test_q10_advanced.py
```bash
$ python examples/Q10/test_q10_advanced.py
[Main Menu]
1. Run basic commands test
2. Test advanced features
3. Check device status
4. Interactive menu
5. Run all tests
```
- Best for: Comprehensive testing and development
- Features: Advanced modes, diagnostics, safety confirmations

## Available Commands

The VacuumTrait provides these commands:

- **Start cleaning** - Initiates a full cleaning cycle
- **Pause cleaning** - Pauses the current cleaning operation
- **Resume cleaning** - Resumes a paused cleaning operation
- **Stop cleaning** - Stops the cleaning operation completely
- **Return to dock** - Sends the robot back to its charging dock

### Advanced Cleaning Modes

Additional cleaning modes can be tested with `test_q10_advanced.py` (option 2):

- **Standard cleaning (cmd=1)** - Full cleaning cycle
- **Electoral/Area cleaning (cmd=2)** - Clean specific areas/zones  
- **Fast map creation (cmd=4)** - Quickly generate room map
  - ⚠️ **Warning**: This will start the robot moving!
  - Requires explicit confirmation before execution

### Device Status Information

The `test_q10_advanced.py` script (option 3) provides:

- **Connected**: Whether device is connected to Roborock services
- **Local connected**: Whether device is reachable on your local network
  - `True` = Direct local connection (LAN/WiFi)
  - `False` = Cloud connection via Roborock servers
- **Available APIs**: 
  - `Command API` = Low-level command interface
  - `Vacuum Trait` = High-level vacuum control interface

## Supported Devices

These scripts are designed for Roborock Q10 devices that support the B01 Q10 protocol. The script will automatically detect if your device has the required `b01_q10_properties` API.

## Troubleshooting

### Device Issues

**"This device doesn't have Q10 properties"**
- Your device may not be a Q10 model
- Check the device model shown in the output
- The device might use a different API (v1_properties, b01_q7_properties, etc.)
- Supported models: Roborock Q10 Series and compatible devices

**Commands not working**
- Ensure device is powered on and connected
- Check that your account has proper permissions
- Try stopping any active cleaning cycle first
- Verify device is online in Roborock app

### Authentication Issues

**"Code login failed"**
- Ensure you entered the code correctly
- Codes expire after a few minutes - request a new one
- Check your email spam folder for the code

**"No cached login data found"**
- Delete cached credentials: `rm ~/.cache/roborock-user-params.pkl`
- Try logging in again with fresh credentials
- Verify your email and password are correct

### Connection Issues

**Commands sent but no response**
- Ensure device is online and connected to the internet
- Check if your WiFi is stable
- Try the device in the official Roborock app first
- Verify the robot can reach Roborock servers

**"Local connected: False"**
- This is normal - device is using cloud connection
- Commands may take a moment longer
- Both local and cloud connections work fine
- If you need local connection, configure device on same network

## Related Documentation

- [PR #754: Add VacuumTrait to q10 devices](https://github.com/Python-roborock/python-roborock/pull/754)
- [PR #758: Add Q10 VacuumTrait Test Scripts](https://github.com/Python-roborock/python-roborock/pull/758)
- [Main example script](../example.py)
- [Supported Features](../../SUPPORTED_FEATURES.md)
- [Device Manager Documentation](../../roborock/devices/README.md)

## Testing Status

✅ **Successfully tested with:**
- Device: Roborock Q10 S5+ (`roborock.vacuum.ss07`)
- All basic commands working (start, pause, resume, stop, return to dock)
- Advanced modes available for testing
- Cloud and local connection modes supported
