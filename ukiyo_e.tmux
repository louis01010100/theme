#!/usr/bin/env bash
# Ukiyo-e tmux theme, run by TPM. Sets only the global style and format
# options of the generated tmux/*.conf files plus two private options.
set -u

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_DATE_FORMAT="%Y-%m-%d"

die() {
    echo "ukiyo_e.tmux: $*" >&2
    exit 1
}

tmux_run() {
    tmux "$@" || die "tmux $* failed"
}

get_option() {
    tmux show-options -gqv "$1"
}

is_on() {
    case "${1,,}" in
        on | 1 | yes | true) return 0 ;;
    esac
    return 1
}

is_off() {
    case "${1,,}" in
        off | 0 | no | false) return 0 ;;
    esac
    return 1
}

time_format() {
    if [ "$(get_option clock-mode-style)" = "12" ]; then
        echo "%I:%M %p"
    else
        echo "%H:%M"
    fi
}

status_file() {
    if is_on "$1"; then
        echo "$CURRENT_DIR/tmux/status-plain.conf"
    else
        echo "$CURRENT_DIR/tmux/status.conf"
    fi
}

apply_status_content() {
    local no_patched_font="$1" date_format="$2" time_format="$3"
    tmux_run set-option -g @ukiyo_e_status_date \
        "${date_format:-$DEFAULT_DATE_FORMAT}"
    tmux_run set-option -g @ukiyo_e_status_time "$time_format"
    tmux_run source-file "$(status_file "$no_patched_font")"
}

main() {
    tmux_run source-file "$CURRENT_DIR/tmux/colors.conf"
    local no_patched_font show_content date_format clock
    no_patched_font="$(get_option @ukiyo_e_no_patched_font)"
    show_content="$(get_option @ukiyo_e_show_status_content)"
    date_format="$(get_option @ukiyo_e_date_format)"
    clock="$(time_format)"
    if ! is_off "$show_content"; then
        apply_status_content "$no_patched_font" "$date_format" "$clock"
    fi
}

main
