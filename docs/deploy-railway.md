# Deploying Auto Browser on Railway

Auto Browser's architecture separates the browser runner (`browser-node`) from the API (`controller`). To run this smoothly on [Railway](https://railway.app/), you need to deploy them as two separate services within a single Railway project.

Both services are pre-configured with `railway.toml` files, making them easy to spin up. Follow these steps:

## Step 1: Create the Railway Services
1. In your Railway dashboard, click **New** -> **GitHub Repo**.
2. Select your cloned Auto Browser repository.
3. During the setup, Railway will try to deploy from the root. Add it anyway.
4. Go to the newly created service's **Settings**, scroll down to **Root Directory**, and set it to `/browser-node`. Rename this service to `browser-node`.
5. Click **New** -> **GitHub Repo** again, select the same repository.
6. Go to its **Settings**, change the **Root Directory** to `/controller`, and rename the service to `controller`.

## Step 2: Configure Networking
The `controller` needs to know how to connect to the Playwright server running inside `browser-node`. Railway provisions internal networking automatically.

1. Go to your `browser-node` service in Railway -> **Settings** -> **Networking** -> **Generate Domain**. Note this internal domain (e.g., `browser-node.up.railway.app` or its `railway.internal` equivalent if you use private networking).
2. Go to your `controller` service -> **Settings** -> **Networking** -> **Generate Domain**.

## Step 3: Set Environment Variables
Go to the **Variables** tab for the `controller` service and add the following:

```env
# Point the controller to the browser node using Railway's internal DNS
BROWSER_WS_ENDPOINT=ws://${{browser-node.RAILWAY_INTERNAL_DOMAIN}}:9223/

# Tell the controller where the visual dashboard is (use the public URL of browser-node)
TAKEOVER_URL=https://${{browser-node.RAILWAY_PUBLIC_DOMAIN}}/vnc.html?autoconnect=true&resize=scale

# Add other required environment variables
API_BEARER_TOKEN=your-super-secret-token
```

> **Note:** The `${{...}}` syntax above allows Railway to inject the correct domains automatically if you use Railway's reference variables. Otherwise, hardcode the domains generated in Step 2.

## Step 4: Storage
Because of the `railway.toml` files, both services will automatically provision a `/data` volume. This ensures browser profiles, downloads, and SQLite databases persist across deployments.

## Step 5: Access the Dashboard
Once both services are running, visit your `controller`'s public domain: `https://<controller-domain>/dashboard`. 
When you click the "Takeover" button on a session, it will correctly route to your `browser-node`'s public VNC URL.
