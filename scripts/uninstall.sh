#!/usr/bin/env bash
set -e

BINARY_NAME="codecontext"
USER_SKILL_DIR="$HOME/.claude/skills/codecontext"
GLOBAL_CONFIG_DIR="$HOME/.codecontext"
UV_TOOL_NAME="codecontext-cli"

echo "🗑️  Uninstalling CodeContext CLI..."
echo

# ============================================================================
# Binary Removal
# ============================================================================

remove_binary() {
    echo "📦 Removing CodeContext binary..."
    echo

    if uv tool list 2>/dev/null | grep -q "$UV_TOOL_NAME"; then
        uv tool uninstall "$UV_TOOL_NAME"
        echo "✅ Removed $UV_TOOL_NAME from UV tools"
    else
        echo "⚠️  $UV_TOOL_NAME not found in UV tools"
    fi

    # Check if binary still exists in PATH
    if command -v "$BINARY_NAME" &> /dev/null; then
        echo "⚠️  $BINARY_NAME still found in PATH: $(which $BINARY_NAME)"
        echo "   You may need to remove it manually"
    else
        echo "✅ $BINARY_NAME removed from PATH"
    fi

    echo
}

# ============================================================================
# Global Configuration Removal
# ============================================================================

remove_global_config() {
    echo "🗄️  Global Configuration"
    echo

    if [ -d "$GLOBAL_CONFIG_DIR" ]; then
        echo "Found global configuration at: $GLOBAL_CONFIG_DIR"
        echo ""
        read -p "Remove global configuration? [y/N]: " choice
        echo

        case "$choice" in
            y|Y)
                rm -rf "$GLOBAL_CONFIG_DIR"
                echo "✅ Removed $GLOBAL_CONFIG_DIR"
                ;;
            *)
                echo "⏭️  Keeping global configuration"
                ;;
        esac
    else
        echo "ℹ️  Global configuration not found at: $GLOBAL_CONFIG_DIR"
    fi

    echo
}

# ============================================================================
# Project Configuration Cleanup
# ============================================================================

cleanup_project_configs() {
    echo "📂 Project Configurations"
    echo

    # Find all .codecontext.toml files
    local found_configs=$(find ~ -maxdepth 5 -name ".codecontext.toml" -type f 2>/dev/null | head -10)

    if [ -n "$found_configs" ]; then
        echo "Found project-level configs (showing up to 10):"
        echo "$found_configs"
        echo ""
        echo "⚠️  These files are NOT automatically removed"
        echo "   Remove them manually from each project if needed:"
        echo "   rm /path/to/project/.codecontext.toml"
    else
        echo "ℹ️  No project-level configs found"
    fi

    echo
}

# ============================================================================
# Claude Code Skill Removal
# ============================================================================

remove_skill() {
    echo "🤖 Claude Code Skill"
    echo

    if [ -d "$USER_SKILL_DIR" ]; then
        echo "Found Claude Code skill at: $USER_SKILL_DIR"
        echo ""
        read -p "Remove Claude Code skill? [y/N]: " choice
        echo

        case "$choice" in
            y|Y)
                rm -rf "$USER_SKILL_DIR"
                echo "✅ Removed $USER_SKILL_DIR"
                ;;
            *)
                echo "⏭️  Keeping Claude Code skill"
                ;;
        esac
    else
        echo "ℹ️  Claude Code skill not found at: $USER_SKILL_DIR"
    fi

    echo
}

# ============================================================================
# Cache Cleanup
# ============================================================================

cleanup_caches() {
    echo "🧹 Cache Cleanup"
    echo

    local caches_to_check=(
        "$HOME/.cache/codecontext"
        "$HOME/Library/Caches/codecontext"  # macOS
    )

    local found_cache=false
    for cache_dir in "${caches_to_check[@]}"; do
        if [ -d "$cache_dir" ]; then
            echo "Found cache at: $cache_dir"
            found_cache=true
        fi
    done

    if [ "$found_cache" = true ]; then
        echo ""
        read -p "Remove all caches? [Y/n]: " choice
        echo

        case "$choice" in
            n|N)
                echo "⏭️  Keeping caches"
                ;;
            *)
                for cache_dir in "${caches_to_check[@]}"; do
                    if [ -d "$cache_dir" ]; then
                        rm -rf "$cache_dir"
                        echo "✅ Removed $cache_dir"
                    fi
                done
                ;;
        esac
    else
        echo "ℹ️  No caches found"
    fi

    echo
}

# ============================================================================
# Python Build Artifacts Cleanup
# ============================================================================

cleanup_python_artifacts() {
    echo "🐍 Python Build Artifacts"
    echo

    # Check if we're in the CodeContext source directory
    if [ ! -d "./packages" ]; then
        echo "ℹ️  Not in CodeContext source directory, skipping"
        echo
        return
    fi

    echo "Found CodeContext source directory"
    echo ""
    read -p "Remove Python build artifacts (__pycache__, *.pyc, build/, dist/)? [Y/n]: " choice
    echo

    case "$choice" in
        n|N)
            echo "⏭️  Keeping build artifacts"
            ;;
        *)
            find packages/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
            find packages/ -type f -name "*.pyc" -delete 2>/dev/null || true
            find packages/ -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
            find packages/ -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
            find packages/ -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
            echo "✅ Removed Python build artifacts"
            ;;
    esac

    echo
}

# ============================================================================
# Main Uninstallation Flow
# ============================================================================

remove_binary
remove_global_config
remove_skill
cleanup_caches
cleanup_python_artifacts
cleanup_project_configs

# ============================================================================
# Final Message
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Uninstallation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🐳 Qdrant server (if running):"
echo "  docker compose -f docker-compose.qdrant.yml down -v"
echo ""
