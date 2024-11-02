# QuizBot

A Socratic learning QuizBot using Streamlit and OpenAI API for PDF-based educational dialogues.

## Author
Created by Sean Harrington  
Director of Technology Innovation  
University of Oklahoma College of Law

## Features
- PDF processing with support for complex formatting
- Socratic dialogue generation using OpenAI GPT-4
- Student analytics and engagement tracking (1-3 grade scale based on interaction level)
- Instructor dashboard for content management
- Multi-user support with role-based access
- Conversation history and transcript generation

## Installation

### Requirements
- Python 3.8+
- PostgreSQL database
- OpenAI API key

### Local Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up PostgreSQL database
4. Configure environment variables:
   ```env
   OPENAI_API_KEY=your_api_key
   PGDATABASE=your_db_name
   PGUSER=your_db_user
   PGPASSWORD=your_db_password
   PGHOST=localhost
   PGPORT=5432
   ```
5. Run the application: `streamlit run main.py`

### Replit Setup
1. Fork the repository on Replit
2. Add the required secrets in Replit's Secrets tab
3. Click Run

## Usage
1. Place your PDF materials in the Readings folder
2. Start a new quiz to engage in Socratic dialogue
3. View analytics and download conversation transcripts

Note: The application will process any PDF files placed in the Readings folder automatically.

## License

MIT License

Copyright (c) 2024 Sean Harrington

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
