# eBird Media Ratings

This project fetches, filters, compares eBird media ratings, and sends email notifications when there are updates in ratings.

## Project Structure

```
ebird_media_ratings_docker
├── src
│   ├── ebird_media_ratings.py  # Main logic for fetching and processing eBird media ratings
├── Dockerfile                   # Instructions to build the Docker image
├── requirements.txt             # Python dependencies required for the project
├── cronjob
│   └── crontab.txt             # Cron job configuration for scheduling the Docker container
├── data                         # Directory for storing CSV data files (created inside the container)
└── README.md                    # Documentation for the project
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd ebird_media_ratings_docker
   ```

2. **Build the Docker image:**
   ```
   docker build -t ebird_media_ratings .
   ```

3. **Run the Docker container:**
   ```
   docker run --rm ebird_media_ratings
   ```

   This will execute the script inside the container and save the data files in the container's `/app/data` directory.

## Usage

- The main script `ebird_media_ratings.py` fetches data from eBird, filters it, compares it with previous data, and sends email notifications if there are updates in ratings.
- The data files (`filtered_data.csv` and `new_filtered_data.csv`) are saved in the `/app/data` directory inside the container.

## Cron Job Configuration

To schedule the script to run periodically, use the `cronjob/crontab.txt` file. Add the following line to your crontab:
```
0 8 * * * docker run --rm ebird_media_ratings
```

If you are using a Docker volume to persist data, update the cron job to include the volume:
```
0 8 * * * docker run --rm -v ebird_data:/app/data ebird_media_ratings
```

## Notes

- Ensure the `config.json` file is correctly configured with your credentials and placed in the project root directory.
- Temporary files like `exported_data.csv.gz` and `exported_data.csv` are cleaned up after processing.
