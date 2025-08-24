/**
 * Cloudflare Worker API for 思源啞口登山步道 (Siyuan Pass Trail)
 * Serves trail coordinate data from D1 database
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 200,
        headers: corsHeaders,
      });
    }

    try {
      // API Routes
      if (path === '/api/trails') {
        return await getTrails(env.DB, corsHeaders);
      }
      
      if (path.startsWith('/api/trail/')) {
        const trailId = path.split('/')[3];
        return await getTrailCoordinates(env.DB, trailId, corsHeaders);
      }

      if (path === '/api/gpx') {
        return await getGPX(env.DB, corsHeaders);
      }

      if (path === '/api/health') {
        return new Response(JSON.stringify({ status: 'ok', timestamp: new Date().toISOString() }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      // Default response
      return new Response(JSON.stringify({
        message: '思源啞口登山步道 API',
        endpoints: [
          '/api/trails - Get all trails',
          '/api/trail/{id} - Get trail coordinates',
          '/api/gpx - Get GPX format',
          '/api/health - Health check'
        ]
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });

    } catch (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
  },
};

/**
 * Get all trails metadata
 */
async function getTrails(db, corsHeaders) {
  const { results } = await db.prepare(`
    SELECT * FROM trail_metadata ORDER BY created_at DESC
  `).all();

  return new Response(JSON.stringify(results), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}

/**
 * Get trail coordinates by trail ID
 */
async function getTrailCoordinates(db, trailId, corsHeaders) {
  // Get trail metadata
  const { results: trail } = await db.prepare(`
    SELECT * FROM trail_metadata WHERE id = ?
  `).bind(trailId).all();

  if (trail.length === 0) {
    return new Response(JSON.stringify({ error: 'Trail not found' }), {
      status: 404,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }

  // Get coordinates
  const { results: coordinates } = await db.prepare(`
    SELECT * FROM trail_coordinates 
    WHERE trail_id = ? 
    ORDER BY sequence_order
  `).bind(trailId).all();

  return new Response(JSON.stringify({
    trail: trail[0],
    coordinates: coordinates
  }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}

/**
 * Generate GPX format for trail
 */
async function getGPX(db, corsHeaders) {
  const trailId = 1; // Default to first trail
  
  // Get trail metadata
  const { results: trail } = await db.prepare(`
    SELECT * FROM trail_metadata WHERE id = ?
  `).bind(trailId).all();

  // Get coordinates
  const { results: coordinates } = await db.prepare(`
    SELECT * FROM trail_coordinates 
    WHERE trail_id = ? 
    ORDER BY sequence_order
  `).bind(trailId).all();

  if (trail.length === 0 || coordinates.length === 0) {
    return new Response('Trail not found', { status: 404 });
  }

  const trailData = trail[0];
  
  // Generate GPX
  let gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Siyuan Trail API" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>${trailData.name}</name>
    <desc>${trailData.description}</desc>
    <time>${new Date().toISOString()}</time>
  </metadata>
  
  <trk>
    <name>${trailData.name}</name>
    <trkseg>`;

  coordinates.forEach(coord => {
    gpx += `
      <trkpt lat="${coord.latitude}" lon="${coord.longitude}">
        <name>${coord.name}</name>`;
    if (coord.description) {
      gpx += `
        <desc>${coord.description}</desc>`;
    }
    gpx += `
      </trkpt>`;
  });

  gpx += `
    </trkseg>
  </trk>
</gpx>`;

  return new Response(gpx, {
    headers: { ...corsHeaders, 'Content-Type': 'application/gpx+xml' },
  });
}