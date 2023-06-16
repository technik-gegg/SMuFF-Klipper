#!/bin/bash
#----------------------------------------------
# SMuFF on Klipper installation script
#----------------------------------------------

# Force script to exit if an error occurs
set -e

# Common runtime vars
HOME_PATH="${HOME}"
KLIPPER_PATH="${HOME}/klipper"
KLIPPER_CONFIG_PATH="${KLIPPER_PATH}_config"                # old config folder; may be replaced by query_instance()
MOONRAKER_CONFIG="${KLIPPER_CONFIG_PATH}/moonraker.conf"    # old config folder; may be replaced by query_instance()
SRCDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"  # source directory taken from the pathname of this script
DEFAULT_INSTANCE="printer_data"                             # default single printer instance folder name

# Module specific runtime vars
MODULES=("smuff.py" "smuff_core.py")                        # modules to symlink
CONFIGS=("smuff.cfg" "smuff_menu.cfg" "smuff_runout.cfg")   # config-files to copy
SYMLINK="${KLIPPER_PATH}/klippy/extras/"                    # symlink folder

UPDATE_INFO="already exists! Please update its contents manually if needed."

# Some colors for highlighting text
WHITE='\e[0;37m'
CYAN='\e[1;36m'
RED='\e[1;31m'
GREEN='\e[1;32m'

# List printer instances
parse_instances()
{
    printf "\nKlipper Printer Instances found:"
    printf "\n--------------------------------\n"
    instances=()
    ndx=1
    default=0
    for entry in $(ls -d ../*_data/ | cut -f2 -d'/') ; do
        printf "${CYAN}%d: %s${WHITE}\n" $ndx $entry
        instances+=($entry)
        if [ $entry == $DEFAULT_INSTANCE ] ; then
            default=$ndx
        fi
        ((ndx+=1))
    done

    while true
    do
        printf "\n"
        read -e -p "Enter the instance number in which to install SMuFF: " -i "${default}" instance

        if [[ $instance > 0 && $instance < $ndx ]] ; then
            KLIPPER_CONFIG_PATH="${HOME_PATH}/${instances[$instance-1]}/config"
            MOONRAKER_CONFIG="${KLIPPER_CONFIG_PATH}/moonraker.conf"
            break
        else
            echo -e "${RED}#${instance} is not contained in the list. Try again or use ^C to abort.${WHITE}"
        fi
    done
}

# Query path to printer instance
query_instance()
{
    if [ -e "${KLIPPER_CONFIG_PATH}" ] ; then
        echo -e "${CYAN}Old Klipper version found, skipping instance parsing...${WHITE}"
    else
        while true ; do
            parse_instances
            printf  "\nSMuFF files will be installed in folder: ${GREEN}%s${WHITE}.\n" ${KLIPPER_CONFIG_PATH}
            read -e -p "Is this correct (y/n)? " -i "y" answer
            if [ $answer == "Y" ] || [ $answer == "y" ] ; then
                echo -e "${GREEN}Ok.${WHITE}"
                break
            fi
        done
    fi
}

# Create a link extension to Klipper
link_extensions()
{
    for mod in ${MODULES[@]} ; do
        if [ ! -L ${SYMLINK}${mod} ] && [ -e ${SYMLINK} ] ; then
            echo "Creating symlink for file ${mod} in ${SYMLINK} ..."
            ln -sf "${SRCDIR}/${mod}" "${SYMLINK}${mod}"
        else
            echo -e "${RED}Link for '${mod}' already exists and is valid, skipping symlink creation.${WHITE}"
        fi
        chmod 644 "${SRCDIR}/${mod}"
    done
}

# Copy config files into the Klipper configs folder
copy_configs()
{
    for cfg in ${CONFIGS[@]} ; do
        if [ -e "${KLIPPER_CONFIG_PATH}/${cfg}" ] ; then
            echo -e "${CYAN}File '${cfg}' ${UPDATE_INFO}${WHITE}"
        else
            echo "Copying ${SRCDIR}/${cfg} to ${KLIPPER_CONFIG_PATH}/${cfg} ..."
            cp "${SRCDIR}/${cfg}" "${KLIPPER_CONFIG_PATH}/"
            chmod 755 "${KLIPPER_CONFIG_PATH}/${cfg}"
        fi
    done
}

# Add updater to moonraker.conf
add_updater()
{
    section=$(grep -c '\[update_manager SMuFF\]' ${MOONRAKER_CONFIG} || true)
    if [ "${section}" -eq 0 ] ; then
        echo "Adding SMuFF update manager section to Moonraker..."
        while read -r line; do
            echo "${line}" >> "${MOONRAKER_CONFIG}"
        done < "${SRCDIR}/moonraker_update_manager.txt"
    else
        echo -e "${RED}SMuFF update manager section ${UPDATE_INFO}${WHITE}"
    fi
}

# Execute steps sequentially
query_instance
link_extensions
copy_configs
add_updater

printf "\n${GREEN}Done.\n\n${CYAN}Don't forget to edit the 'smuff.cfg' file before you restart the firmware!${WHITE}\n\n\n"
