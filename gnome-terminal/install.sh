#!/usr/bin/env bash
# Install, update, set as default, or remove the "Ukiyo-e" GNOME
# Terminal profile. Colours come from the generated palette.sh.
#
# usage: install.sh [--set-default | --uninstall] [-h | --help]
# exit:  0 success, 2 usage error, 3 missing prerequisite,
#        4 a gsettings call failed
set -u

UUID="5a1c0e9b-7d3f-4b6a-8e2d-4f0a9c6b1e37"
PROFILE_SCHEMA="org.gnome.Terminal.Legacy.Profile"
PROFILE_PATH="/org/gnome/terminal/legacy/profiles:/:$UUID/"
PROFILES_LIST="org.gnome.Terminal.ProfilesList"
PROFILE_KEYS=(visible-name use-theme-colors background-color
    foreground-color palette cursor-colors-set cursor-background-color
    cursor-foreground-color highlight-colors-set
    highlight-background-color highlight-foreground-color
    bold-color-same-as-fg)
COLOUR_VARS=(UKIYO_E_BACKGROUND UKIYO_E_FOREGROUND UKIYO_E_CURSOR_BG
    UKIYO_E_CURSOR_FG UKIYO_E_SELECTION_BG UKIYO_E_SELECTION_FG)
HEX_RE="^#[0-9a-fA-F]{6}$"
ENTRY_RE="'#[0-9a-fA-F]{6}'"
PALETTE_RE="^\[$ENTRY_RE(, $ENTRY_RE){15}\]$"
HEX4="[0-9a-fA-F]{4}"
UUID_RE="[0-9a-fA-F]{8}-$HEX4-$HEX4-$HEX4-[0-9a-fA-F]{12}"

MODE="install"
SET_DEFAULT=0
UUIDS=()

usage() {
    echo "usage: install.sh [--set-default | --uninstall] [-h | --help]"
}

die() {
    local code="$1"
    shift
    echo "install.sh: $*" >&2
    exit "$code"
}

script_dir() {
    local source="${BASH_SOURCE[0]}"
    [[ $source == */* ]] || source="./$source"
    cd "${source%/*}" && pwd
}

parse_args() {
    local arg uninstall=0
    for arg in "$@"; do
        case "$arg" in
            --set-default) SET_DEFAULT=1 ;;
            --uninstall) uninstall=1 ;;
            -h | --help)
                usage
                exit 0
                ;;
            *)
                usage >&2
                die 2 "unknown argument: $arg"
                ;;
        esac
    done
    if ((SET_DEFAULT && uninstall)); then
        usage >&2
        die 2 "--set-default and --uninstall are mutually exclusive"
    fi
    ((uninstall)) && MODE="uninstall"
    return 0
}

has_line() {
    local text="$1" line="$2"
    [[ $'\n'"$text"$'\n' == *$'\n'"$line"$'\n'* ]]
}

load_palette() {
    local file name
    file="$(script_dir)/palette.sh" || die 3 "cannot locate palette.sh"
    [[ -f $file ]] || die 3 "missing $file"
    # shellcheck source=palette.sh
    source "$file" || die 3 "cannot read $file"
    for name in "${COLOUR_VARS[@]}"; do
        [[ ${!name:-} =~ $HEX_RE ]] || die 3 "palette.sh: bad $name"
    done
    [[ ${UKIYO_E_PALETTE:-} =~ $PALETTE_RE ]] ||
        die 3 "palette.sh: bad UKIYO_E_PALETTE"
}

preflight() {
    command -v gsettings >/dev/null ||
        die 3 "gsettings not found on PATH"
    has_line "$(gsettings list-schemas 2>/dev/null)" "$PROFILES_LIST" ||
        die 3 "GSettings schema $PROFILES_LIST is not installed"
    has_line "$(gsettings list-relocatable-schemas 2>/dev/null)" \
        "$PROFILE_SCHEMA" ||
        die 3 "GSettings schema $PROFILE_SCHEMA is not installed"
    load_palette
}

set_profile_key() {
    local key="$1" value="$2"
    has_line "$(printf '%s\n' "${PROFILE_KEYS[@]}")" "$key" ||
        die 4 "refusing to write profile key $key"
    gsettings set "$PROFILE_SCHEMA:$PROFILE_PATH" "$key" "$value" ||
        die 4 "gsettings failed to write $key"
}

set_list_key() {
    local key="$1" value="$2"
    [[ $key == list || $key == default ]] ||
        die 4 "refusing to write $PROFILES_LIST $key"
    gsettings set "$PROFILES_LIST" "$key" "$value" ||
        die 4 "gsettings failed to write $PROFILES_LIST $key"
}

get_uuids() {
    local raw
    raw="$(gsettings get "$PROFILES_LIST" list)" ||
        die 4 "gsettings failed to read $PROFILES_LIST list"
    UUIDS=()
    while [[ $raw =~ $UUID_RE ]]; do
        UUIDS+=("${BASH_REMATCH[0]}")
        raw="${raw#*"${BASH_REMATCH[0]}"}"
    done
}

format_list() {
    if (($# == 0)); then
        echo "@as []"
        return
    fi
    local joined
    joined="$(printf ", '%s'" "$@")"
    echo "[${joined:2}]"
}

get_default() {
    local raw
    raw="$(gsettings get "$PROFILES_LIST" default)" ||
        die 4 "gsettings failed to read $PROFILES_LIST default"
    raw="${raw#\'}"
    echo "${raw%\'}"
}

install_profile() {
    set_profile_key visible-name "'Ukiyo-e'"
    set_profile_key use-theme-colors false
    set_profile_key background-color "'$UKIYO_E_BACKGROUND'"
    set_profile_key foreground-color "'$UKIYO_E_FOREGROUND'"
    set_profile_key palette "$UKIYO_E_PALETTE"
    set_profile_key cursor-colors-set true
    set_profile_key cursor-background-color "'$UKIYO_E_CURSOR_BG'"
    set_profile_key cursor-foreground-color "'$UKIYO_E_CURSOR_FG'"
    set_profile_key highlight-colors-set true
    set_profile_key highlight-background-color "'$UKIYO_E_SELECTION_BG'"
    set_profile_key highlight-foreground-color "'$UKIYO_E_SELECTION_FG'"
    set_profile_key bold-color-same-as-fg true
}

register() {
    get_uuids
    has_line "$(printf '%s\n' "${UUIDS[@]}")" "$UUID" && return 0
    set_list_key list "$(format_list "${UUIDS[@]}" "$UUID")"
}

set_default() {
    set_list_key default "'$UUID'"
}

uninstall() {
    local uuid default listed=0 remaining=()
    get_uuids
    for uuid in "${UUIDS[@]}"; do
        if [[ $uuid == "$UUID" ]]; then
            listed=1
        else
            remaining+=("$uuid")
        fi
    done
    default="$(get_default)" || exit 4
    if [[ $default == "$UUID" && ${#remaining[@]} -eq 0 ]]; then
        gsettings reset "$PROFILES_LIST" default || die 4 "reset default"
        gsettings reset "$PROFILES_LIST" list || die 4 "reset list"
    else
        [[ $default == "$UUID" ]] &&
            set_list_key default "'${remaining[0]}'"
        ((listed)) && set_list_key list "$(format_list "${remaining[@]}")"
    fi
    gsettings reset-recursively "$PROFILE_SCHEMA:$PROFILE_PATH" ||
        die 4 "gsettings failed to reset $PROFILE_PATH"
}

main() {
    parse_args "$@"
    preflight
    if [[ $MODE == uninstall ]]; then
        uninstall
        echo "install.sh: removed profile Ukiyo-e ($UUID)" >&2
        return 0
    fi
    install_profile
    register
    ((SET_DEFAULT)) && set_default
    echo "install.sh: installed profile Ukiyo-e ($UUID)" >&2
}

main "$@"
