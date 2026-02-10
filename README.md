# dublin-bikes-team20

# Project Overview
This project builds a web application that:

-Collects bike station data from JCDecaux API

-Collects weather data from OpenWeather API

-Stores data in MySQL

-Displays stations and availability on a map

-Predicts bike availability using Machine Learning

-Runs as a Flask web app (to be deployed on EC2)

# Team Workflow
This explains how every team member should set up and work on this repository

1. Clone the Repository
    - Clone with this link
```py
git clone https://github.com/shayan-ashish-chakraborty/dublin-bikes-team20.git
```


```
cd dublin-bikes-team20
```

2. Switch to Dev Branch
    - We will not directly work on main branch
```py
git checkout dev
```
    - If it says branch not found
```
git fetch
git checkout dev
```

3. Daily Workflow
    - Before starting to work everyday
    - This ensures your code is updated
    - After making changes
```py
git checkout dev
git pull origin dev
```

```
git add .
git commit -m "Describe what you did"
git push
```

Important
- Never push directly to main
- Never use git push --force
- Always pull before staring work

4. Branch Structure
    - When the project is complete and tested
    - dev will be merged into main

```py
main -> Stable version (final submission ready)
dev -> All development happens here
```
