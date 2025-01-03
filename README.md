# MemeStream - Social Media Feed Application

A full-stack social media-style feed application built with Quart (Python) and vanilla JavaScript. The application features an infinite scrolling feed of memes (images and videos) with like functionality.

## Features

- **Infinite Scrolling Feed**: Automatically loads more content as you scroll
- **Media Support**: Handles both images and videos
- **Like System**: Double-tap to like posts
- **Responsive Design**: Optimized for mobile and desktop
- **Video Controls**: Mute/unmute videos with a floating button
- **Database Integration**: Stores media in PostgreSQL database
- **Discord Integration**: Automatically fetches memes from Discord channels

## Tech Stack

### Backend
- **Quart**: Python async web framework
- **PostgreSQL**: Database for storing media and metadata
- **asyncpg**: Async PostgreSQL client
- **Hypercorn**: ASGI server

### Frontend
- Vanilla JavaScript
- IntersectionObserver API for infinite scrolling
- Native HTML5 video player
- Feather Icons

## Setup

### Prerequisites
- Python 3.8+
- PostgreSQL
- Node.js (for frontend development)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/social-feed.git
   cd social-feed
   ```

2. Set up virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up PostgreSQL database:
   ```sql
   CREATE DATABASE memedb;
   CREATE USER memedb_user WITH PASSWORD 'yourpassword';
   GRANT ALL PRIVILEGES ON DATABASE memedb TO memedb_user;
   ```

5. Create configuration file:
   ```bash
   cp private_conf.example.py private_conf.py
   ```
   Edit `private_conf.py` with your database credentials and Discord API tokens.

6. Run the application:
   ```bash
   python app.py
   ```

7. Access the application at `http://localhost:5001`

## Usage

### Adding Memes
1. Run the meme downloader:
   ```bash
   python download_meme.py
   ```
   This will fetch memes from configured Discord channels and store them in the database.

### Using the Feed
- Scroll vertically to browse memes
- Double-tap to like a post
- Click the mute button to toggle video sound
- Click a video to pause/play

## Project Structure

```
.
├── app.py                # Main application
├── download_meme.py      # Meme downloader script
├── meme_db.py            # Database models
├── test_db.py            # Database tests
├── private_conf.py       # Configuration file
├── requirements.txt      # Python dependencies
├── static/               # Static files
│   └── js/               # JavaScript files
│       ├── feedManager.js # Feed management logic
│       ├── main.js       # Main frontend logic
│       └── videoManager.js # Video management logic
└── templates/            # HTML templates
    └── index.html        # Main template
```

## License

MIT License

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
