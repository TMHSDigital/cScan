# Setting Up GitHub Pages for cScan Documentation

## Quick Setup

### 1. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click on **Settings** → **Pages**
3. Under "Source", select **Deploy from a branch**
4. Choose **main** branch and **/docs** folder
5. Click **Save**

Your documentation will be available at:
```
https://YOUR-USERNAME.github.io/cScan/
```

### 2. Update Links

Replace `TMHSDigital` with your actual GitHub username in these files (already done):
- `docs/index.md`
- `docs/_config.yml`
- `README.md`

### 3. Local Development (Optional)

To preview the site locally:

```bash
# Install Jekyll (one-time setup)
gem install bundler jekyll

# Navigate to docs folder
cd docs

# Create Gemfile
echo 'source "https://rubygems.org"' > Gemfile
echo 'gem "github-pages", group: :jekyll_plugins' >> Gemfile

# Install dependencies
bundle install

# Run local server
bundle exec jekyll serve

# View at http://localhost:4000
```

## Documentation Structure

```
cScan/
├── docs/                        # GitHub Pages documentation
│   ├── index.md                 # Home page
│   ├── _config.yml              # Jekyll configuration
│   ├── README.md                # Full user manual
│   ├── CROSS_PLATFORM_GUIDE.md  # Platform-specific guide
│   ├── IMPROVEMENTS.md          # Feature documentation
│   ├── FIXES_APPLIED.md         # Technical fixes
│   ├── DOCUMENTATION_REVIEW.md  # Documentation overview
│   └── .nojekyll                # Ensures all files are processed
├── cScan.py                     # Main script
├── cScan_config.ini             # Configuration
├── requirements.txt             # Python dependencies
├── LICENSE                      # MIT License
├── README.md                    # Quick start (points to docs)
└── .gitignore                   # Git ignore file
```

## Customization

### Themes

The current theme is `jekyll-theme-cayman`. You can change it in `_config.yml`:
- `jekyll-theme-slate`
- `jekyll-theme-minimal`
- `jekyll-theme-architect`
- `jekyll-theme-dinky`

### Custom Domain

To use a custom domain:
1. Create a file named `CNAME` in the docs folder
2. Add your domain (e.g., `cscan.example.com`)
3. Configure DNS settings with your domain provider

## Troubleshooting

### Page Not Building

Check the Actions tab in your GitHub repository for build errors.

### 404 Errors

- Ensure GitHub Pages is enabled
- Check that you selected the `/docs` folder
- Wait 10-20 minutes for initial deployment

### Theme Not Working

GitHub Pages only supports certain themes. Use one from the [supported themes list](https://pages.github.com/themes/). 