# 思源啞口登山步道 API (Siyuan Pass Trail API)

Cloudflare Worker API for serving hiking trail coordinates from OpenStreetMap Way #810113984.

## 🗺️ Trail Information

- **Trail Name**: 思源啞口登山步道 (Siyuan Pass Trail)
- **OSM Way ID**: 810113984
- **Total Points**: 74 coordinates
- **Location**: Taiwan
- **Trail Type**: Hiking track from 思源啞口 to 南湖大山 勝光登山口

## 🚀 Quick Start

### Prerequisites
- Node.js installed
- Cloudflare account
- Wrangler CLI installed

### Setup

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Create D1 database**
   ```bash
   npm run db:create
   ```

3. **Update wrangler.toml**
   - Copy the database ID from the previous command
   - Update `database_id` in `wrangler.toml`

4. **Run migrations and seed data**
   ```bash
   npm run db:setup
   ```

5. **Start development server**
   ```bash
   npm run dev
   ```

## 📊 Database Schema

### trail_metadata
- Trail information and bounds
- OSM metadata (way ID, changeset, etc.)

### trail_coordinates  
- Individual coordinate points
- Sequence order and waypoint markers
- Linked to trail metadata

## 🔗 API Endpoints

### GET `/api/trails`
Returns all trail metadata
```json
{
  "id": 1,
  "osm_way_id": 810113984,
  "name": "思源啞口登山步道",
  "total_nodes": 74,
  "min_lat": 24.3698934,
  "max_lat": 24.3709985
}
```

### GET `/api/trail/{id}`
Returns trail with all coordinates
```json
{
  "trail": {...},
  "coordinates": [
    {
      "latitude": 24.3707927,
      "longitude": 121.3429648,
      "sequence_order": 1,
      "name": "Trail Point 1"
    }
  ]
}
```

### GET `/api/gpx`
Returns GPX format for GPS devices

### GET `/api/health`
Health check endpoint

## 🛠️ Development Commands

```bash
# Development server
npm run dev

# Deploy to production
npm run deploy

# Database operations
npm run db:migrate    # Run migrations
npm run db:seed      # Seed with trail data
npm run db:setup     # Migrate + seed

# Query database directly
npm run db:query "SELECT COUNT(*) FROM trail_coordinates"
```

## 📁 Project Structure

```
├── src/
│   └── index.js          # Main Worker script
├── migrations/
│   └── 0001_*.sql        # Database migrations
├── schema.sql            # Complete schema
├── insert_data.sql       # Trail coordinate data
├── wrangler.toml         # Cloudflare configuration
└── package.json
```

## 🗺️ Data Sources

- **OpenStreetMap**: Way #810113984
- **Created by**: 台灣紫斑蝶
- **Last edited**: ~5 years ago
- **Changeset**: #85996831

## 📍 Trail Coordinates

The database contains 74 precise GPS coordinates covering the complete trail from 思源啞口 to 南湖大山 勝光登山口, suitable for:

- GPS navigation devices
- Hiking mobile apps
- Trail mapping applications
- Route planning tools

## 🌐 Deployment

Deploy to Cloudflare Workers:

```bash
npm run deploy
```

The API will be available at: `https://your-worker.your-subdomain.workers.dev`

## 📄 License

MIT License - Feel free to use this data for hiking, mapping, and outdoor applications.