<h2>Command to run (in port 8000)</h2>

```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```



<h2>Deployment Commands</h2>

<h3>Make the necessary changes in the server and test locally and save it</h3>

<h3>Make sure docker is running in background</h3>

<h3>Build the dockerfile</h3>

```bash
docker build -t nutrition-api .   
```

<h3>Tag the dockerfile</h3>

```bash
tag nutrition-api a3km/nutrition-api:latest        
```

<h3>Deploy the updated the dockerfile</h3>

```bash
docker push a3km/nutrition-api:latest 
```

<h3>Go the settings in render and manual deloy the latest dockerimage</h3>

<h3>To run the dockerImage locally</h3>

```bash
docker run -d --name fitness-backend -p 8000:8000 --env-file .env nutrition-api
```

