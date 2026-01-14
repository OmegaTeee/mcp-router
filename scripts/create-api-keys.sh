# Add secret(s) to Keychain
ks add huggingface_api_key "YOUR-HUGGINGFACE_API_KEY" &&
ks add obsidian_api_key "YOUR-OBSIDIAN-API-KEY"
# ks add figma_api_key "YOUR-FIGMA-API-KEY"
# ks add github_token "YOUR-GITHUB-TOKEN"
# ks add ollama_api_key "YOUR-OLLAMA_API_KEY"

# Regenerate .env
./scripts/gen-env-from-ks.sh