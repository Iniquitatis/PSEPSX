# PSEPSX
PSEPSX is a mod builder and a mod itself for PowerSlave Exhumed that aims to provide various in-game changes to bring the game a bit closer to the PlayStation version.  



## Features
* Builder application for configuring each and every aspect of this mod<sup>1</sup>
* Ported<sup>2</sup> PlayStation maps
* Various gameplay changes
* Various graphics changes
* Various audio changes

<sup>1</sup> — Within reasonable boundaries, of course.  
<sup>2</sup> — The original PlayStation maps are already included in the PowerSlave Exhumed, however they aren't activated in the first place and have some compatibility issues. All of that were resolved in this mod.



## Downloading

### Release Builds
[Here](https://github.com/Iniquitatis/PSEPSX/releases/download/v1.1.0/PSEPSX_v1.1.0.zip) (builder)  
**OR**  
[Here](https://github.com/Iniquitatis/PSEPSX/releases/download/v1.1.0/PSEPSX.kpf) (pre-built mod)

### Development Builds
[Here](https://github.com/Iniquitatis/PSEPSX/releases/download/latest/PSEPSX.zip) (builder)

***NOTE:** Although I thoroughly test every change, it is still more likely for bugs to occur in the development builds.*



## Installation

### Builder Application
<img src="Screenshots/Builder.png?raw=true">

1. At launch, the application will try to detect your PowerSlave Exhumed installation directory.
    * If that's the case, you can just skip to the next step.
    * If you don't see anything in the top text fields (_Game Directory_ and _Output Directory_), or paths are incorrect, or you just want to place the mod somewhere else:
        1. Press the *...* button next to the _Game Directory_ text field.
        2. Select the directory where the game is installed.
        3. Press the *...* button next to the _Output Directory_ text field.
        4. Select the directory where the mod should be placed after building (preferably to the `%game_root%/mods` to avoid cutting/pasting the resulting mod).
2. Check the desired options from the list with checkboxes below.
3. Press the **Build** button.

If you want to reconfigure the mod, just repeat the above operations.

### Pre-built Mod
Put the `PSEPSX.kpf` file into the `%game_root%/mods` directory.  
**EXAMPLE:** `C:\Program Files (x86)\Steam\steamapps\PowerSlave Exhumed\mods`

***NOTE:** The pre-built mod contains every possible setting enabled, so if you want to customize the experience, it is advised to use the builder application.*



## FAQ
**Q:** Why use the builder app? Couldn't you just add the configuration menu directly to the game?  
**A:** Unfortunately, the game doesn't allow adding any new menu entries, so there's no chance, at least for now. Also, this mod brings some changes that cannot be applied at runtime. To put it simply, the scripting system is quite constrained for doing something like that.



## License
See LICENSE file in the root of this repository.
