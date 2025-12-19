# Disable Password Prompts

This script configures Ubuntu to not ask for passwords when:
- Running sudo commands
- Starting applications
- Unlocking keyrings

## Usage

```bash
cd /home/hsthind/Documents/GitHub/REIMS2/setup-scripts
sudo bash disable-password-prompts.sh
```

## What It Does

1. **Configures passwordless sudo**: Adds your user to `/etc/sudoers` with `NOPASSWD` privilege
2. **Configures polkit**: Allows passwordless authentication for common operations
3. **Disables keyring prompts**: Configures GNOME keyring to unlock automatically
4. **Configures autostart**: Sets up keyring to start automatically

## Security Warning

⚠️ **WARNING**: Disabling password prompts reduces system security. Only use this on:
- Personal development machines
- Trusted systems
- Systems behind a firewall

**DO NOT** use this on:
- Production servers
- Shared systems
- Systems exposed to the internet

## Verification

After running the script, test with:
```bash
sudo whoami
```

You should not be prompted for a password.

## Reverting Changes

To re-enable password prompts:

1. Remove from sudoers:
   ```bash
   sudo visudo
   # Remove the line: username ALL=(ALL:ALL) NOPASSWD: ALL
   ```

2. Remove polkit rules:
   ```bash
   sudo rm /etc/polkit-1/rules.d/49-nopasswd_global.rules
   ```

3. Remove keyring autostart:
   ```bash
   rm ~/.config/autostart/gnome-keyring-pkcs11.desktop
   ```

