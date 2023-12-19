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
ICONDIR="${SRCDIR}/KlipperScreen-images"                    # source directory for KlipperScreen images
DEFAULT_INSTANCE="printer_data"                             # default single printer instance folder name
LOGS_PATH="${DEFAULT_INSTANCE}/logs"                        # default path for Klipper logfiles
SMUFF_LOG_FILE="/var/tmp/smuff.log"                         # default path for SMuFF logfile
KLIPPERSCREEN_PATH="${HOME}/KlipperScreen"                  # path for KlipperScreen
KS_THEMES_PATH="${KLIPPERSCREEN_PATH}/styles"               # path for KlipperScreen themes

# Module specific runtime vars
MODULES=("smuff.py" "smuff_core.py")                        # modules to symlink
CONFIGS=("smuff.cfg" "smuff_menu.cfg" "smuff_menu_ks.cfg" "smuff_runout.cfg")   # config-files to copy
SYMLINK="${KLIPPER_PATH}/klippy/extras/"                    # symlink folder
ICONS=("smuff.svg" "close_lid.svg" "cut_filament.svg" "instance_a.svg" "instance_b.svg" "load_filament.svg" "open_lid.svg" "purge_filament.svg" "reset.svg" "swap_tools.svg" "unjam.svg" "unload_filament.svg" "wipe_nozzle.svg")   # image-files to copy
THEMES=("colorized" "material-dark" "material-darker" "material-light" "z-bolt")   # default KlipperScreen theme folders

ALREADY_EXISTS="already exists!"
UPDATE_INFO="${ALREADY_EXISTS} Please update its contents manually if needed."
UPDATE_INFO_ICON="${ALREADY_EXISTS} Please copy it manually if needed."

# Some colors for highlighting text
WHITE='\e[0;37m'
CYAN='\e[1;36m'
RED='\e[1;31m'
GREEN='\e[1;32m'
WARNING='\e[41m\e[1;37m'

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
            LOGS_PATH="${HOME_PATH}/${instances[$instance-1]}/logs"
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
            printf  "\nThe target folder will be: ${GREEN}%s${WHITE}.\n" ${KLIPPER_CONFIG_PATH}
            read -e -p "Is this correct (y/n)? " -i "y" answer
            if [ $answer == "Y" ] || [ $answer == "y" ] ; then
                echo -e "${GREEN}Ok.${WHITE}"
                break
            fi
        done
    fi
}

# Create symlinks in Klipper 'extras' folder
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

# Remove symlinks from Klipper 'extras' folder
unlink_extensions()
{
    for mod in ${MODULES[@]} ; do
        if [ -L ${SYMLINK}${mod} ] ; then
            echo "Removing symlink for file ${mod} in ${SYMLINK} ..."
            rm "${SYMLINK}${mod}"
        else
            echo -e "${RED}Link for '${mod}' does not exist.${WHITE}"
        fi
    done
}

# Create symlink in printer 'logs' folder
link_logfile()
{
    if [ ! -L ${LOGS_PATH}/smuff.log ] ; then
        echo "*Created*" > "${SMUFF_LOG_FILE}"
        echo "Creating symlink for logfile ..."
        ln -sf "${SMUFF_LOG_FILE}" "${LOGS_PATH}/smuff.log"
    else
        echo -e "${RED}Link for 'smuff.log' already exists and is valid, skipping symlink creation.${WHITE}"
    fi
}

# Remove symlink in printer 'logs' folder
unlink_logfile()
{
    if [ -L ${LOGS_PATH}/smuff.log ] ; then
        echo "Removing symlink for logfile ..."
        rm "${LOGS_PATH}/smuff.log"
    else
        echo -e "${RED}Link for 'smuff.log' does not exist.${WHITE}"
    fi
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

# Copy image files into the KlipperScreen styles folders
copy_images()
{
    if [ -e "${KLIPPERSCREEN_PATH}" ] ; then
        for theme in ${THEMES[@]} ; do
            if [ -e "${KS_THEMES_PATH}/${theme}/" ] ; then
                for icon in ${ICONS[@]} ; do
                    if [ -e "${KS_THEMES_PATH}/${theme}/${icon}" ] ; then
                        echo -e "${CYAN}File '${icon}' ${UPDATE_INFO_ICON}${WHITE}"
                    else
                        echo "Copying ${ICONDIR}/${icon} to ${KS_THEMES_PATH}/${theme}/${icon} ..."
                        cp "${ICONDIR}/${icon}" "${KS_THEMES_PATH}/${theme}/"
                        chmod 644 "${KS_THEMES_PATH}/${theme}/${icon}"
                    fi
                done
            fi
        done
    else
        echo -e "${CYAN}KlipperScreen folder not found, skipping copying images!${WHITE}"
    fi
}

# Delete config files from the Klipper configs folder
delete_configs()
{
    for cfg in ${CONFIGS[@]} ; do
        if [ -e "${KLIPPER_CONFIG_PATH}/${cfg}" ] ; then
            echo "Removing ${KLIPPER_CONFIG_PATH}/${cfg} ..."
            rm "${KLIPPER_CONFIG_PATH}/${cfg}"
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
force_uninst=0
if [ -n "$1" ] && [ $1 == "uninstall" ] ; then
    printf "\n${WARNING}*** WARNING! This script will remove all SMuFF files. ***${WHITE}\n\n"
    printf "\n${CYAN}Do you want to proceed (y/n)? ${WHITE}"
    read -e -i "n" answer
    if [ $answer == "N" ] || [ $answer == "n" ] ; then
        echo -e "${GREEN}Aborted.${WHITE}"
        exit -1
    fi
    force_uninst=1
fi
query_instance
if [ $force_uninst == 1 ] ; then
    unlink_extensions
    unlink_logfile
    delete_configs
    cd ${HOME_PATH}
    printf "\n${CYAN}Do you want me to delete the installation folder ${SRCDIR} (y/n)? ${WHITE}"
    read -e -i "n" answer
    if [ $answer == "Y" ] || [ $answer == "y" ] ; then
        rm -r -f ${SRCDIR}
        rmdir ${SRCDIR}
    fi

    printf "\n${GREEN}Done.\n\n${CYAN}Don't forget to remove the updater in moonraker.conf manually!${WHITE}\n\n\n"
else
    link_extensions
    link_logfile
    copy_configs
    copy_images
    add_updater

    printf "\n${GREEN}Done.\n\n${CYAN}Don't forget to edit the 'smuff.cfg' file before you restart the firmware!${WHITE}\n\n\n"
fi
