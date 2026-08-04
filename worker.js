export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    if (request.headers.get('Upgrade') === 'websocket') {
      const railwayUrl = `https://${env.RAILWAY_DOMAIN}${url.pathname}`;
      const modifiedRequest = new Request(railwayUrl, {
        method: request.method,
        headers: request.headers
      });
      return fetch(modifiedRequest);
    }
    
    return Response.redirect(`https://${env.RAILWAY_DOMAIN}/dashboard`, 301);
  }
}
