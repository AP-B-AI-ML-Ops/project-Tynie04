#!/bin/bash
set -e

copied=0

if [ ! -f .env ]; then
    cp .env.example .env
    copied=1
    printf "\n"
    printf "########################################################\n"
    printf "#                                                      #\n"
    printf "#   WARNING: .env was created from .env.example        #\n"
    printf "#                                                      #\n"
    printf "#   Action required: open .env and replace all         #\n"
    printf "#   'change_me' values before starting any services.   #\n"
    printf "#                                                      #\n"
    printf "########################################################\n"
    printf "\n"
fi


if [ "$copied" = "1" ]; then
    printf "Sleeping 5 seconds so you can read the warnings above...\n"
    sleep 5
fi
