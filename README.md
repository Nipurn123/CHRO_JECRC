# Ultimate CHRO Finder with Gemini 1.5 Flash

A powerful tool to find Chief Human Resources Officers (CHROs) using multiple AI-powered search methods and generate comprehensive summaries using Google's Gemini 1.5 Flash.

## Features

- Multi-source CHRO search using:
  - Perplexity AI
  - OpenAI (ChatGPT)
  - Google (Gemini)
  - LinkedIn (JECRC method)
- Automated browser interactions
- Real-time progress tracking
- Comprehensive summary generation
- Company database management
- LinkedIn profile viewing capabilities

## Prerequisites

- Python 3.9+
- Google Chrome browser
- Gemini API key
- OpenAI API key (optional)
- LinkedIn credentials (optional)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with:
```env
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key  # Optional
LINKEDIN_USERNAME=your_linkedin_email  # Optional
LINKEDIN_PASSWORD=your_linkedin_password  # Optional
```

## Project Structure

```
.
├── README.md
├── requirements.txt
├── ultimate.py
└── tools/
    ├── __init__.py
    ├── google_search.py
    ├── openai_search.py
    ├── perplexity_search.py
    └── jecrc_search.py
```

## Usage

1. Start the application:
```bash
python ultimate.py
```

2. Access the web interface at `http://localhost:7860`

3. Enter a company name and click "Search"

4. View results from all search methods and the final summary

## Features in Detail

### Search Methods

1. **Perplexity AI Search**
   - Direct web search with AI-powered analysis
   - Real-time information gathering

2. **OpenAI (ChatGPT) Search**
   - Natural language processing
   - Context-aware responses

3. **Google (Gemini) Search**
   - Advanced search capabilities
   - Direct integration with Google's Gemini API

4. **JECRC (LinkedIn) Search**
   - Professional network data extraction
   - Verified professional information

### Additional Features

- **Company Database**: Store and manage search results
- **LinkedIn Integration**: Direct profile viewing
- **Progress Tracking**: Real-time search progress monitoring
- **Error Handling**: Robust error management and recovery
- **Rate Limiting**: Smart handling of API rate limits

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini API
- OpenAI API
- Perplexity AI
- LinkedIn
- Selenium WebDriver
- Gradio Team 