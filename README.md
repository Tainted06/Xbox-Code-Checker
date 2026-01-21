# This project is no longer being maintained 
# If you'd like to buy the project from me, this repo and the source code of the paid version, contact @TaintedDev on telegram.

<div align="center">
    <h1>Xbox/Microsoft Code Checker</h1>
    <p>Checks Microsoft/Xbox codes for valid, invalid, and used codes! This does not check Windows licenses. A paid version with more features is avaliable, contact @TaintedDev on telegram for more information.</p>
    <img src="https://img.shields.io/github/downloads/Tainted06/Xbox-Code-Checker/total?style=flat">
    <img src="https://img.shields.io/github/stars/Tainted06/Xbox-Code-Checker?style=flat">
    <img src="https://img.shields.io/github/forks/Tainted06/Xbox-Code-Checker?style=flat">
    <br>
    <img src="https://github.com/Tainted06/Xbox-Code-Checker/blob/main/github-demo-0.png?raw=true">
    <br>
    <p><i>⭐ Star the repo to support future projects 🙏</i></p>
</div>

# Paid verion avaliable!
- Input is email:password, not WLID
- Can handle multiple accounts better
- Has proxy support
- Better output and fixed issues with the geography locked codes
## Contact @TaintedDev on telegram or @Tainted.Dev on discord for more information
<br>
<img src="https://github.com/Tainted06/Xbox-Code-Checker/blob/main/github-demo-1.jpg?raw=true">

# Xbox Code Checker
1. [Overview](https://github.com/Tainted06/Xbox-Code-Checker#xbox-code-checker)
2. [How to run from compiled](https://github.com/Tainted06/Xbox-Code-Checker#run-from-compiled)
3. [How to run from source](https://github.com/Tainted06/Xbox-Code-Checker#run-from-source)
4. [What WLID is and how to get it](https://github.com/Tainted06/Xbox-Code-Checker#what-is-wlid-and-how-to-get-it) 
5. [Using multiple WLIDs](https://github.com/Tainted06/Xbox-Code-Checker#using-multiple-wlids) 
6. [Other](https://github.com/Tainted06/Xbox-Code-Checker#other)

# Overview 
This is a simple proof-of-concept tool to check Xbox codes. This could be used to check Xbox gamepass codes from discord nitro or anything else. It just sends a single request for checking the code. 

**This is my first time programming in GoLang, so the code isn't perfect, if there's something that could be better feel free to make a [pull request](https://github.com/Tainted06/Xbox-Code-Checker/pulls) or an [issue](https://github.com/Tainted06/Xbox-Code-Checker/issues) and I'll look into it!**

# Run from compiled
**Only works on windows**
1. Open [Releases](https://github.com/Tainted06/Xbox-Code-Checker/releases)
2. Download the latest version
3. Extract the files out of the .zip file
4. Add your codes in input\codes.txt
5. Get your [WLID](https://github.com/Tainted06/Xbox-Code-Checker#what-is-wlid-and-how-to-get-it) and add it in input\wlid.txt
6. Run XboxChecker.exe
7. After it's done the working, used, and invalid codes will be saved output\working.txt, output\used.txt, output\invalid.txt

# Run from source
1. Download GoLang from their [website](https://go.dev/dl/)
2. Go to [Releases](https://github.com/Tainted06/Xbox-Code-Checker/releases)
3. Download the *source code* of the latest release
4. Extract the files
5. Add your codes in input\codes.txt
6. Get your [WLID](https://github.com/Tainted06/Xbox-Code-Checker#what-is-wlid-and-how-to-get-it) and add it in input\wlid.txt
7. Open terminal/cmd, navigate to the directory of the code
8. Run the command `go run main.go` or `go build`
9. After it's done the working, used, and invalid codes will be saved output\working.txt, output\used.txt, output\invalid.txt

# What is WLID and how to get it
WLID *(probably stands for Windows Live ID)* is a code that Microsoft uses to authenticate your account, it is needed for this program to send the requests for checking the codes.

How to get it:

1. Open [redeem.microsoft.com](http://redeem.microsoft.com/)
2. Click `F12`, `CTRL + Shift + I`, or open devtools
3. Go to the network tab
4. Type any code into the redeem code field 
5. Look for a request in the network tab called PrepareRedeem
6. Click it, look at the headers
7. Find where it says Authorization, right-click the value of authorization, and click copy value
8. This is your WLID

# Using Multiple WLIDs
You can use multiple WLIDs with this tool, just add each wlid on a new line in the WLID input file.

# Other
This is 100% for educational reasons, don't use it for anything else. This tool is free for people to use and learn from, don't try selling it.


# Credits
- The first part of this readme was inspired by https://github.com/itschasa/Discord-Backup
