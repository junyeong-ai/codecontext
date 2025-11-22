#!/usr/bin/env bash
# Setup jemalloc for optimal PyTorch CPU inference
#
# Usage:
#   ./scripts/setup-jemalloc.sh          # Install and configure
#   ./scripts/setup-jemalloc.sh --check  # Check current status
#   ./scripts/setup-jemalloc.sh --help   # Show help

set -e

COLOR_RESET="\033[0m"
COLOR_GREEN="\033[0;32m"
COLOR_YELLOW="\033[0;33m"
COLOR_RED="\033[0;31m"
COLOR_BLUE="\033[0;34m"

info() {
    echo -e "${COLOR_BLUE}ℹ${COLOR_RESET} $1"
}

success() {
    echo -e "${COLOR_GREEN}✓${COLOR_RESET} $1"
}

warn() {
    echo -e "${COLOR_YELLOW}⚠${COLOR_RESET} $1"
}

error() {
    echo -e "${COLOR_RED}✗${COLOR_RESET} $1"
}

show_help() {
    cat << EOF
Setup jemalloc for optimal PyTorch CPU inference

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --check     Check current allocator status
    --install   Install jemalloc (default)
    --help      Show this help message

BACKGROUND:
    PyTorch CPU mode suffers from memory fragmentation during long-running
    inference, especially with variable batch sizes. jemalloc is designed
    to minimize this fragmentation.

    Performance improvements (PyTorch official benchmarks):
    • Peak memory reduction: 34%
    • Average memory reduction: 53%
    • Up to 2.2x speedup in transformer workloads

    Reference: https://pytorch.org/blog/optimizing-libtorch/

EXAMPLES:
    # Check if jemalloc is already configured
    $0 --check

    # Install and configure jemalloc
    $0

    # Run codecontext with jemalloc
    LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 codecontext index
EOF
}

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

check_jemalloc() {
    info "Checking jemalloc status..."
    echo

    # Check LD_PRELOAD
    if [[ -n "$LD_PRELOAD" ]] && [[ "$LD_PRELOAD" == *"jemalloc"* ]]; then
        success "LD_PRELOAD configured: $LD_PRELOAD"
    else
        warn "LD_PRELOAD not configured for jemalloc"
    fi

    # Check MALLOC_CONF
    if [[ -n "$MALLOC_CONF" ]]; then
        success "MALLOC_CONF: $MALLOC_CONF"
    else
        warn "MALLOC_CONF not set (optional optimization)"
    fi

    # Check if jemalloc is installed
    local os_type=$(detect_os)
    local jemalloc_path=""

    if [[ "$os_type" == "linux" ]]; then
        # Try common paths
        for path in \
            "/usr/lib/x86_64-linux-gnu/libjemalloc.so.2" \
            "/usr/lib/x86_64-linux-gnu/libjemalloc.so.1" \
            "/usr/lib64/libjemalloc.so" \
            "/usr/local/lib/libjemalloc.so"; do
            if [[ -f "$path" ]]; then
                jemalloc_path="$path"
                break
            fi
        done
    elif [[ "$os_type" == "macos" ]]; then
        # Try homebrew path
        if command -v brew &> /dev/null; then
            local brew_prefix=$(brew --prefix jemalloc 2>/dev/null || echo "")
            if [[ -n "$brew_prefix" ]]; then
                jemalloc_path="$brew_prefix/lib/libjemalloc.dylib"
            fi
        fi
    fi

    if [[ -n "$jemalloc_path" ]] && [[ -f "$jemalloc_path" ]]; then
        success "jemalloc installed: $jemalloc_path"
        echo
        info "To use jemalloc with codecontext:"
        echo "  LD_PRELOAD=$jemalloc_path codecontext index"
        echo
        info "For persistent configuration, add to shell profile:"
        echo "  export LD_PRELOAD=$jemalloc_path"
        return 0
    else
        error "jemalloc not found"
        return 1
    fi
}

install_jemalloc() {
    local os_type=$(detect_os)

    info "Installing jemalloc for $os_type..."
    echo

    if [[ "$os_type" == "linux" ]]; then
        # Detect package manager
        if command -v apt-get &> /dev/null; then
            info "Using apt-get (Debian/Ubuntu)"
            sudo apt-get update
            sudo apt-get install -y libjemalloc-dev
            success "jemalloc installed"
        elif command -v yum &> /dev/null; then
            info "Using yum (RHEL/CentOS)"
            sudo yum install -y jemalloc-devel
            success "jemalloc installed"
        elif command -v dnf &> /dev/null; then
            info "Using dnf (Fedora)"
            sudo dnf install -y jemalloc-devel
            success "jemalloc installed"
        else
            error "No supported package manager found"
            info "Install manually: https://github.com/jemalloc/jemalloc/wiki/Getting-Started"
            return 1
        fi
    elif [[ "$os_type" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            info "Using Homebrew"
            brew install jemalloc
            success "jemalloc installed"
        else
            error "Homebrew not found"
            info "Install Homebrew: https://brew.sh"
            return 1
        fi
    else
        error "Unsupported OS: $os_type"
        return 1
    fi

    echo
    check_jemalloc
}

configure_optimal_malloc_conf() {
    info "Optimal MALLOC_CONF for long-running inference:"
    echo
    cat << 'EOF'
export MALLOC_CONF="oversize_threshold:1,background_thread:true,metadata_thp:auto,dirty_decay_ms:9000000000,muzzy_decay_ms:9000000000"
EOF
    echo
    info "Add this to your shell profile (~/.bashrc, ~/.zshrc) for persistence"
}

main() {
    local command="${1:-install}"

    case "$command" in
        --help|-h)
            show_help
            exit 0
            ;;
        --check)
            check_jemalloc
            exit $?
            ;;
        --install|install|"")
            if check_jemalloc 2>/dev/null; then
                success "jemalloc already configured"
                echo
                configure_optimal_malloc_conf
                exit 0
            fi

            install_jemalloc
            if [[ $? -eq 0 ]]; then
                echo
                configure_optimal_malloc_conf
            fi
            ;;
        *)
            error "Unknown command: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

main "$@"
