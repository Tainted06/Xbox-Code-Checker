package main

// Imports
import (
	"encoding/json"
	"io/ioutil"
	"strconv"
	"math/rand"
	"net/http"
	"os/exec"
	"strings"
	"bufio"
	"time"
	"fmt"
	"os"
)

func main() {

	// Clear console
	cmd := exec.Command("cmd", "/c", "cls")
	cmd.Stdout = os.Stdout
	cmd.Run()

	// Title screen
	setTitle("Xbox Code Checker | Made by Tainted | github.com/Tainted06/Xbox-Code-Checker")
	fmt.Println("\033[36m █ █ ██▄ ███ █ █    ███ ███ ██▄ ███    ███ █ █ ███ ███ █ █ ███ ███\n  █  █▄█ █ █  █     █   █ █ █ █ █▄     █   █▄█ █▄  █   ██▄ █▄  █▄ \n █ █ █▄█ █▄█ █ █    ███ █▄█ ███ █▄▄    ███ █ █ █▄▄ ███ █ █ █▄▄ █ █\n By: Tainted [tainted.dev] [github.com/Tainted06]\n\033[0m")

	// Reading WLID(s)
	wlid, err := os.Open("input\\WLID.txt")
	if err != nil {
		fmt.Println("\033[31m", err)
		time.Sleep(5 * time.Second)
		os.Exit(1)
	}
	fileScannerWLIDs := bufio.NewScanner(wlid)
	fileScannerWLIDs.Split(bufio.ScanLines)
	var wlids []string
	for fileScannerWLIDs.Scan() {
		if strings.Contains(fileScannerWLIDs.Text(), "WLID1.0=") {
			wlids = append(wlids, string(fileScannerWLIDs.Text()))
		} else {
			wlids = append(wlids, "WLID1.0=\"" + string(fileScannerWLIDs.Text()) + "\"")
		}		
	}
	if len(wlids) == 0 {
		fmt.Println("\033[31m No WLIDs found in input\\WLID.txt")
		time.Sleep(5 * time.Second)
		os.Exit(1)
	}

	// Reading codes
	codes_file, err := os.Open("input\\codes.txt")
	if err != nil {
		fmt.Println("\033[31m", err)
		time.Sleep(5 * time.Second)
		os.Exit(1)
	}

	// Go through each line
	fileScannerCodes := bufio.NewScanner(codes_file)
	fileScannerCodes.Split(bufio.ScanLines)
	var codes []string
	for fileScannerCodes.Scan() {
		codes = append(codes, string(fileScannerCodes.Text()))
	}
	if len(codes) == 0 {
		fmt.Println("\033[31m No codes found in input\\codes.txt")
		time.Sleep(5 * time.Second)
		os.Exit(1)
	}

	// Starting amount
	startamt := len(codes)
	// Iterating through codes
	for {

		// Set title
		percent_done := strconv.Itoa((startamt - len(codes)) * 100 / startamt)
		setTitle("Xbox Code Checker | github.com/Tainted06/Xbox-Code-Checker | " + strconv.Itoa(startamt - len(codes)) + "/" + strconv.Itoa(startamt) + " codes checked | " + percent_done + "% done")

		// Check if codes is empty
		if len(codes) != 0 {

			// Checking if codes is less than 18 characters
			if len(codes[0]) < 18 {
				fmt.Println("\033[31m", " [-] "+codes[0]+" is invalid!")
				f, _ := os.OpenFile("output\\invalid.txt", os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0600)
				defer f.Close()
				f.WriteString(codes[0] + "\n")

				// Remove code from slice
				codes = codes[1:]

			} else {

			// Sending request
			client := &http.Client{}
			req, err1 := http.NewRequest("GET", "https://purchase.mp.microsoft.com/v7.0/tokenDescriptions/"+codes[0]+"?market=US&language=en-US&supportMultiAvailabilities=true", nil)
			req.Header.Add("accept", "application/json, text/javascript, */*; q=0.01")
			req.Header.Add("accept-encoding", "gzip, deflate, br")
			req.Header.Add("accept-language", "en-US,en;q=0.8")
			req.Header.Add("authorization", string(wlids[rand.Intn(len(wlids))]))
			req.Header.Add("origin", "https://www.microsoft.com")
			req.Header.Add("referer", "https://www.microsoft.com/")
			req.Header.Add("sec-fetch-dest", "empty")
			req.Header.Add("sec-fetch-mode", "cors")
			req.Header.Add("sec-fetch-site", "same-site")
			req.Header.Add("sec-gpc", "1")
			req.Header.Add("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36")
			resp, err2 := client.Do(req)

			// Parsing json
			content, err3 := (ioutil.ReadAll(resp.Body))
			var json_content map[string]interface{}
			json.Unmarshal([]byte(content), &json_content)

			// Checking for ratelimit
			if resp.StatusCode == 429 {
				fmt.Println("\033[31m", " [-] Ratelimit! [Try adding more WLIDs or waiting for the ratelimit to finish]")
				time.Sleep(5 * time.Second)
			} else

			// Checking response
			{
				if err1 != nil || err2 != nil || err3 != nil {
					fmt.Println("\033[31m", " [-] Error: ", err1, err2, err3)
				} else if strings.Contains(string(content), "tokenState") {
					tknstate := json_content["tokenState"].(string)
					if string(tknstate) == "Active" {
						fmt.Println("\033[32m", " [+] "+codes[0][0:17]+"-XXXXX-XXXXX is valid!")
						f, _ := os.OpenFile("output\\working.txt", os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0600)
						defer f.Close()
						f.WriteString(codes[0] + "\n")
					} else if string(tknstate) == "Redeemed" {
						fmt.Println("\033[31m", " [-] "+codes[0][0:17]+"-XXXXX-XXXXX is used!")
						f, _ := os.OpenFile("output\\used.txt", os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0600)
						defer f.Close()
						f.WriteString(codes[0] + "\n")
					}
				} else if json_content["code"] != "undefined" {
					if json_content["code"] == "NotFound" {
						fmt.Println("\033[31m", " [-] "+codes[0][0:17]+"-XXXXX-XXXXX is invalid!")
						f, _ := os.OpenFile("output\\invalid.txt", os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0600)
						defer f.Close()
						f.WriteString(codes[0] + "\n")
					} else if json_content["code"] == "Unauthorized" {
						fmt.Println("\033[31m", " [-] Error: Invalid WLID")
						time.Sleep(5 * time.Second)
						os.Exit(1)
					}
				} else {
					fmt.Println("\033[31m", " [-] Error: "+string(content))
				}

				// Remove code from slice
				codes = codes[1:]

			}
		}
		} else {
			break // Leave loop once all codes have been checked
		}
	}

	fmt.Println("\033[36m", "\nFinished checking codes!")
	time.Sleep(30 * time.Second)
}

// Change console title
func setTitle(title string) {
	cmd := exec.Command("cmd", "/C", "title", title)
	cmd.Stdout = os.Stdout
	cmd.Run()
}