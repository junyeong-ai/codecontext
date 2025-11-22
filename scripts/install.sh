#!/usr/bin/env bash
set -e

BINARY_NAME="codecontext"
SKILL_NAME="codecontext"
PROJECT_SKILL_DIR=".claude/skills/$SKILL_NAME"
USER_SKILL_DIR="$HOME/.claude/skills/$SKILL_NAME"
GLOBAL_CONFIG_DIR="$HOME/.codecontext"
GLOBAL_CONFIG_FILE="$GLOBAL_CONFIG_DIR/config.toml"

echo "🚀 Installing CodeContext CLI..."
echo

# ============================================================================
# Dependency Checks
# ============================================================================

check_dependencies() {
    echo "🔍 Checking dependencies..."
    echo

    # Check UV
    if ! command -v uv &> /dev/null; then
        echo "❌ UV is not installed"
        echo
        echo "Please install UV first:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo
        echo "Or use Homebrew:"
        echo "  brew install uv"
        echo
        exit 1
    else
        echo "✅ UV installed: $(uv --version)"
    fi

    # Check Python 3.13
    if ! uv python list | grep -q "3.13"; then
        echo "⚠️  Python 3.13 not found"
        echo
        read -p "Install Python 3.13 via UV? [Y/n]: " choice
        case "$choice" in
            n|N)
                echo "❌ Python 3.13 is required for CodeContext"
                exit 1
                ;;
            *)
                echo "📦 Installing Python 3.13..."
                uv python install 3.13
                echo "✅ Python 3.13 installed"
                ;;
        esac
    else
        echo "✅ Python 3.13 available"
    fi

    echo
}

# ============================================================================
# Skill Installation Functions
# ============================================================================

get_skill_version() {
    local skill_md="$1"
    if [ -f "$skill_md" ]; then
        grep "^version:" "$skill_md" 2>/dev/null | sed 's/version: *//' || echo "unknown"
    else
        echo "unknown"
    fi
}

check_skill_exists() {
    [ -d "$USER_SKILL_DIR" ] && [ -f "$USER_SKILL_DIR/SKILL.md" ]
}

compare_versions() {
    local ver1="$1"
    local ver2="$2"

    if [ "$ver1" = "$ver2" ]; then
        echo "equal"
    elif [ "$ver1" = "unknown" ] || [ "$ver2" = "unknown" ]; then
        echo "unknown"
    else
        if [ "$(printf '%s\n' "$ver1" "$ver2" | sort -V | head -n1)" = "$ver1" ]; then
            if [ "$ver1" != "$ver2" ]; then
                echo "older"
            else
                echo "equal"
            fi
        else
            echo "newer"
        fi
    fi
}

backup_skill() {
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_dir="$USER_SKILL_DIR.bak-$timestamp"

    echo "📦 Creating backup: $backup_dir"
    cp -r "$USER_SKILL_DIR" "$backup_dir"
    echo "   ✅ Backup created successfully"
}

install_user_level_skill() {
    echo "📋 Installing skill to $USER_SKILL_DIR"

    mkdir -p "$(dirname "$USER_SKILL_DIR")"
    cp -r "$PROJECT_SKILL_DIR" "$USER_SKILL_DIR"

    echo "   ✅ User-level skill installed successfully"
}

install_project_level_skill() {
    echo "✅ Project-level skill already available at: $PROJECT_SKILL_DIR"
    echo "   This skill is project-specific and works when Claude Code is opened here."
}

prompt_skill_installation() {
    if [ ! -d "$PROJECT_SKILL_DIR" ]; then
        echo "ℹ️  No Claude Code skill found in project"
        return 0
    fi

    local project_version=$(get_skill_version "$PROJECT_SKILL_DIR/SKILL.md")

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🤖 Claude Code Skill Installation"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "This project includes a Claude Code skill for CodeContext."
    echo "The skill enables Claude to search codebases using hybrid search."
    echo ""
    echo "Skill: $SKILL_NAME (v$project_version)"
    echo ""

    # Check if user-level skill exists
    if check_skill_exists; then
        local existing_version=$(get_skill_version "$USER_SKILL_DIR/SKILL.md")
        local comparison=$(compare_versions "$existing_version" "$project_version")

        echo "Status: Already installed at user-level (v$existing_version)"
        echo ""

        case "$comparison" in
            equal)
                echo "✅ You have the latest version installed"
                echo ""
                read -p "Reinstall anyway? [y/N]: " choice
                case "$choice" in
                    y|Y)
                        backup_skill
                        rm -rf "$USER_SKILL_DIR"
                        install_user_level_skill
                        ;;
                    *)
                        echo "   ⏭️  Skipped"
                        ;;
                esac
                ;;
            older)
                echo "🔄 New version available: v$project_version"
                echo ""
                read -p "Update to v$project_version? [Y/n]: " choice
                case "$choice" in
                    n|N)
                        echo "   ⏭️  Keeping current version"
                        ;;
                    *)
                        backup_skill
                        rm -rf "$USER_SKILL_DIR"
                        install_user_level_skill
                        echo "   ✅ Updated to v$project_version"
                        ;;
                esac
                ;;
            newer)
                echo "⚠️  Your installed version (v$existing_version) is newer than project version (v$project_version)"
                echo ""
                read -p "Downgrade to v$project_version? [y/N]: " choice
                case "$choice" in
                    y|Y)
                        backup_skill
                        rm -rf "$USER_SKILL_DIR"
                        install_user_level_skill
                        ;;
                    *)
                        echo "   ⏭️  Keeping current version"
                        ;;
                esac
                ;;
            *)
                echo "⚠️  Version comparison failed"
                echo ""
                read -p "Reinstall anyway? [y/N]: " choice
                case "$choice" in
                    y|Y)
                        backup_skill
                        rm -rf "$USER_SKILL_DIR"
                        install_user_level_skill
                        ;;
                    *)
                        echo "   ⏭️  Skipped"
                        ;;
                esac
                ;;
        esac
    else
        # No existing user-level skill - show installation options
        echo "Installation options:"
        echo ""
        echo "  [1] Skip      - Don't install skill (you can install later)"
        echo "  [2] User      - Install to ~/.claude/skills/ (RECOMMENDED)"
        echo "  [3] Project   - Keep in ./.claude/skills/ (current project only)"
        echo "  [4] Both      - Install to both locations (user + project)"
        echo ""
        read -p "Choose installation option [1-4] (default: 2): " choice
        echo

        case "$choice" in
            1)
                echo "⏭️  Skill installation skipped"
                echo ""
                echo "To install later:"
                echo "  • User-level:    cp -r $PROJECT_SKILL_DIR ~/.claude/skills/"
                echo "  • Project-level: Already available at $PROJECT_SKILL_DIR"
                ;;
            2|"")
                install_user_level_skill
                echo ""
                echo "🎉 Skill installed successfully!"
                echo ""
                echo "Claude Code can now:"
                echo "  • Search codebases with hybrid search"
                echo "  • Explore code architecture"
                echo "  • Find API dependencies"
                echo "  • Track code relationships"
                ;;
            3)
                echo ""
                install_project_level_skill
                ;;
            4)
                install_user_level_skill
                echo ""
                install_project_level_skill
                echo ""
                echo "🎉 Skill installed at both locations!"
                ;;
            *)
                echo "❌ Invalid option. Skipping skill installation."
                echo ""
                echo "To install later, run this script again or copy manually:"
                echo "  cp -r $PROJECT_SKILL_DIR ~/.claude/skills/"
                ;;
        esac
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ============================================================================
# Global Configuration Setup
# ============================================================================

setup_global_config() {
    echo ""
    echo "📝 Setting up global configuration..."
    echo

    mkdir -p "$GLOBAL_CONFIG_DIR"

    if [ -f "$GLOBAL_CONFIG_FILE" ]; then
        echo "✅ Global config already exists at: $GLOBAL_CONFIG_FILE"
        echo ""
        read -p "Overwrite with default config? [y/N]: " choice
        case "$choice" in
            y|Y)
                create_default_config
                ;;
            *)
                echo "   ⏭️  Keeping existing config"
                ;;
        esac
    else
        create_default_config
    fi
}

create_default_config() {
    cat > "$GLOBAL_CONFIG_FILE" << 'EOF'
# CodeContext Configuration - Optimized for RRF Hybrid Search

[embeddings]
provider = "huggingface"

[embeddings.huggingface]
model_name = "jinaai/jina-code-embeddings-0.5b"
device = "auto"
batch_size = 16
normalize_embeddings = true
max_length = 32768
cleanup_interval = 5
use_jemalloc = true

[storage]
provider = "qdrant"

[storage.qdrant]
mode = "remote"
url = "http://localhost:6333"
fusion_method = "rrf"
prefetch_ratio_dense = 7.0
prefetch_ratio_sparse = 3.0
upsert_batch_size = 100
enable_performance_logging = false

[indexing]
file_chunk_size = 30
batch_size = 64
languages = ["python", "kotlin", "java", "javascript", "typescript", "markdown"]
max_file_size_mb = 10
parallel_workers = 1

[indexing.field_weights]
name = 15
qualified_name = 12
signature = 10
docstring = 8
content = 6
filename = 4
file_path = 2
k1 = 1.2
b = 0.75
avg_dl = 100.0

[search]
default_limit = 10
enable_graph_expansion = true
graph_max_hops = 1
graph_ppr_threshold = 0.4
graph_score_weight = 0.3
max_chunks_per_file = 2
diversity_preserve_top_n = 1

[search.type_boosting]
class = 0.12
method = 0.10
function = 0.10
enum = 0.08
interface = 0.06
markdown = 0.05
type = 0.04
config = 0.03
field = 0.02
variable = 0.0

[translation]
enabled = false

[logging]
level = "INFO"
EOF

    echo "✅ Global config created: $GLOBAL_CONFIG_FILE"
    echo "   Customize: codecontext config edit"
}

# ============================================================================
# Binary Installation
# ============================================================================

install_binary() {
    echo "📦 Installing CodeContext via UV tool..."
    echo

    # Check if already installed
    if uv tool list | grep -q "codecontext-cli"; then
        echo "⚠️  CodeContext is already installed"
        echo ""
        read -p "Reinstall? [Y/n]: " choice
        case "$choice" in
            n|N)
                echo "   ⏭️  Skipping installation"
                return 0
                ;;
            *)
                echo "🔄 Reinstalling..."
                echo "🧹 Cleaning Python caches..."
                find packages/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
                find packages/ -type f -name "*.pyc" -delete 2>/dev/null || true
                find packages/ -type f -name "*.pyo" -delete 2>/dev/null || true
                uv tool uninstall codecontext-cli || true
                ;;
        esac
    fi

    # Install from local workspace with all local dependencies in editable mode
    uv tool install --python 3.13 \
      --with ./packages/codecontext-core \
      --with ./packages/codecontext-storage-qdrant \
      --with ./packages/codecontext-embeddings-huggingface \
      --with peft \
      --editable ./packages/codecontext-cli

    echo
    echo "✅ CodeContext installed successfully!"
    echo
}

check_installation() {
    echo "🔍 Verifying installation..."
    echo

    if command -v codecontext &> /dev/null; then
        codecontext version
        echo
        echo "✅ CodeContext is ready to use!"
    else
        echo "⚠️  codecontext command not found in PATH"
        echo
        echo "UV tool installs to: ~/.local/bin"
        echo
        echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.) if needed:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo
        echo "Then reload your shell:"
        echo "  source ~/.zshrc  # or ~/.bashrc"
    fi
    echo
}

# ============================================================================
# Main Installation Flow
# ============================================================================

check_dependencies
install_binary
check_installation
setup_global_config
prompt_skill_installation

# ============================================================================
# Final Message
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Installation Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚙️  Start Qdrant (required for remote mode):"
echo "   docker compose -f docker-compose.qdrant.yml up -d"
echo ""
echo "   Or use embedded mode (no Docker required):"
echo "   Edit config: codecontext config edit"
echo "   Set: [storage.qdrant.mode] = \"embedded\""
echo ""
echo "📝 Quick Start:"
echo "   cd /path/to/your/project"
echo "   codecontext index"
echo "   codecontext search \"authentication\""
echo ""
echo "📚 Commands:"
echo "   codecontext list-projects        # List all indexed projects"
echo "   codecontext delete-project NAME  # Delete a project"
echo "   codecontext status               # Show system status"
echo "   codecontext config edit          # Edit global config"
echo ""
echo "📂 Config: $GLOBAL_CONFIG_FILE"
echo ""
echo "📖 Documentation: https://github.com/junyeong-ai/codecontext"
echo ""
