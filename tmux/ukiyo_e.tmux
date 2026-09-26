#!/usr/bin/env bash
# Ukiyo-e tmux theme, run by the run-shell line or by configure.py. Sets
# only the global style and format options of the rendered tmux/*.conf
# files next to it plus two private options.
set -u

# Resolved physically once, so one load reads one version.
CURRENT_DIR="$(cd -P -- "$(dirname -- "$0")" && pwd -P)"
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

apply_status_content() {
    local date_format="$1" time_format="$2"
    tmux_run set-option -g @ukiyo_e_status_date \
        "${date_format:-$DEFAULT_DATE_FORMAT}"
    tmux_run set-option -g @ukiyo_e_status_time "$time_format"
    tmux_run source-file "$CURRENT_DIR/tmux/status.conf"
}

main() {
    tmux_run source-file "$CURRENT_DIR/tmux/colors.conf"
    local show_content date_format clock
    show_content="$(get_option @ukiyo_e_show_status_content)"
    date_format="$(get_option @ukiyo_e_date_format)"
    clock="$(time_format)"
    if ! is_off "$show_content"; then
        apply_status_content "$date_format" "$clock"
    fi
}

main
