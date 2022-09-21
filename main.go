package main   

// Imports
import (
	"encoding/json"
	"io/ioutil"
    "net/http"
	"os/exec"
	"strings"
    "bufio"
	"time"
	"fmt"
	"os"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
)

func main() {  

	// Clear console
	cmd := exec.Command("cmd", "/c", "cls")
	cmd.Stdout = os.Stdout; cmd.Run()

	// Title screen
	fmt.Println("\033[36m █ █ ██▄ ███ █ █    ███ ███ ██▄ ███    ███z █ █ ███ ███ █ █ ███ ███\n  █  █▄█ █ █  █     █   █ █ █ █ █▄     █   █▄█ █▄  █   ██▄ █▄  █▄ \n █ █ █▄█ █▄█ █ █    ███ █▄█ ███ █▄▄    ███ █ █ █▄▄ ███ █ █ █▄▄ █ █\n By: Tainted [tainted.dev] [github.com/Tainted06]\n\033[0m")

	// Reading WLID
	wlid, err := os.ReadFile("input\\WLID.txt")
	if err != nil {
		fmt.Println("\033[31m", err)
		time.Sleep(5 * time.Second)   
		os.Exit(1)
	}

	// Reading codes
	codes, err := os.Open("input\\codes.txt")
	if err != nil {
		fmt.Println("\033[31m", err)
		time.Sleep(5 * time.Second)   
		os.Exit(1)
	}

	// Splitting lines
	fileScanner := bufio.NewScanner(codes)
	fileScanner.Split(bufio.ScanLines)

	// Iterating through lines
	for fileScanner.Scan() {

		// Sending request
		client := &http.Client{}
		req, err1 := http.NewRequest("GET", "https://purchase.mp.microsoft.com/v7.0/tokenDescriptions/" + fileScanner.Text() + "?market=US&language=en-US&supportMultiAvailabilities=true", nil)
		req.Header.Add("accept", "application/json, text/javascript, */*; q=0.01")
		req.Header.Add("accept-encoding", "gzip, deflate, br")
		req.Header.Add("accept-language", "en-US,en;q=0.8")
		req.Header.Add("authorization", string(wlid))
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
			fmt.Println("\033[31m", " [-] Ratelimit! [For a version with proxies and threading visit https://tainted.tools]")
		} else

		// Checking response
		{
			if (err1 != nil || err2 != nil || err3 != nil) {
				fmt.Println("\033[31m", " [-] Error: ", err1, err2, err3)
			} else if strings.Contains(string(content), "tokenState") {
				tknstate := json_content["tokenState"].(string)
				if string(tknstate) == "Active" {
					fmt.Println("\033[32m", " [+] " + fileScanner.Text()[0:17] + "-XXXXX-XXXXX is valid!")
					f, _ := os.OpenFile("output\\working.txt", os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0600)
					defer f.Close()
					f.WriteString(fileScanner.Text() + "\n");
				} else if string(tknstate) == "Redeemed" {
					fmt.Println("\033[31m", " [-] " + fileScanner.Text()[0:17] + "-XXXXX-XXXXX is used!")
					f, _ := os.OpenFile("output\\used.txt", os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0600)
					defer f.Close()
					f.WriteString(fileScanner.Text() + "\n");
				}
			} else if json_content["code"] != "undefined" {
				if json_content["code"] == "NotFound" {
					fmt.Println("\033[31m", " [-] " + fileScanner.Text()[0:17] + "-XXXXX-XXXXX is invalid!")
					f, _ := os.OpenFile("output\\invalid.txt", os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0600)
					defer f.Close()
					f.WriteString(fileScanner.Text() + "\n");
				} else if json_content["code"] == "Unauthorized" {
					fmt.Println("\033[31m", " [-] Error: Invalid WLID")
					time.Sleep(5 * time.Second)   
					os.Exit(1)
				}
			} else {
				fmt.Println("\033[31m", " [-] Error: " + string(content))
			}
		}
    }

	fmt.Println("\033[36m", "\nFinished checking codes!")
	time.Sleep(30 * time.Second)   
}