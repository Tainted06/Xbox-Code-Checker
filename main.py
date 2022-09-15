# Imports
import os
import time
import fade
import requests
from colorama import Fore

# Title screen
os.system('cls' if os.name in ('nt', 'dos') else 'clear')
print(fade.purpleblue(
"""█ █ ██▄ ███ █ █    ███ ███ ██▄ ███    ███ █ █ ███ ███ █ █ ███ ███
 █  █▄█ █ █  █     █   █ █ █ █ █▄     █   █▄█ █▄  █   ██▄ █▄  █▄ 
█ █ █▄█ █▄█ █ █    ███ █▄█ ███ █▄▄    ███ █ █ █▄▄ ███ █ █ █▄▄ █ █
By: Tainted [tainted.dev] [github.com/Tainted06]"""))

# Main function
def main():

    # Read WLID
    wlid = open("input\\WLID.txt").read() 

    for code in open("input\\codes.txt").read().splitlines():

        # Sending request
        r = requests.get(
            "https://purchase.mp.microsoft.com/v7.0/tokenDescriptions/" + code + "?market=US&language=en-US&supportMultiAvailabilities=true",
            headers = {
                "accept" : "application/json, text/javascript, */*; q=0.01",
                "accept-encoding" : "gzip, deflate, br",
                "accept-language" : "en-US,en;q=0.8",
                "authorization" : wlid,
                "origin" : "https://www.microsoft.com",
                "referer" : "https://www.microsoft.com/",
                "sec-fetch-dest" : "empty",
                "sec-fetch-mode" : "cors",
                "sec-fetch-site" : "same-site",
                "sec-gpc" : "1",
                "user-agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"
            }
        )

        # Checking code
        if "tokenState" in r.text:
            if r.json()['tokenState'] == "Active":
                print(f"{Fore.GREEN}[+] {code[0:17]}-XXXXX-XXXXX is valid!")
                with open('output\\working.txt', 'a') as f:
                    f.write(code + "\n")
            elif r.json()['tokenState'] == "Redeemed":
                print(f"{Fore.RED}[-] {code[0:17]}-XXXXX-XXXXX is used!")
                with open('output\\used.txt', 'a') as f:
                    f.write(code + "\n")
        elif 'code' in r.json():
            if r.json()['code'] == "NotFound":
                print(f"{Fore.RED}[-] {code[0:17]}-XXXXX-XXXXX is invalid!")
                with open('output\\invalid.txt', 'a') as f:
                    f.write(code + "\n")
            if r.json()['code'] == "Unauthorized":
                print(f"{Fore.RED}[-] Your WLID is invalid!")
                time.sleep(5)
                quit()
        else:
            print(f"{Fore.RED}[-] Error: " + r.text)

    print("\n" + Fore.CYAN + "Finished checking codes!\n")

# Starting
if __name__ == "__main__":
    main()