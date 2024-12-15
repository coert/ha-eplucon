#!/bin/bash
curl -s -c cookies.txt https://portaal.eplucon.nl/login > login_page.html
csrf_token=$(grep -oP '<meta name="csrf-token" content="\K[^"]+' login_page.html)
token=$(grep -oP '<input type="hidden" name="_token" value="\K[^"]+' login_page.html)
valid_from=$(grep -zoP '<input name="valid_from"[^>]*value="([^"]*)"' login_page.html | sed -n 's/.*value="\([^"]*\)".*/\1/p')
my_name=$(grep -oP '<input id="my_name[^"]*"' login_page.html | sed -n 's/.*id="\([^"]*\)".*/\1/p')
echo $my_name:
echo valid_from: $valid_from
echo _token: $csrf_token
echo username: $username
echo password: \*\*\*\*\*
echo remember: 1
echo submit:
curl -s -b cookies.txt -D headers.txt -L -c cookies.txt \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Origin: https://portaal.eplucon.nl"\
  -H "Referer: https://portaal.eplucon.nl/login"\
  -d --data-urlencode "$my_name=" \
     --data-urlencode "valid_from=$valid_from" \
     --data-urlencode "_token=$csrf_token" \
     --data-urlencode "username=$username" \
     --data-urlencode "password=$password" \
     -d "remember=1" https://portaal.eplucon.nl/login > /dev/null
rm login_page.html
rm headers.txt