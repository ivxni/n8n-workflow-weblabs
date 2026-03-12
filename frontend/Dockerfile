FROM node:20-alpine

WORKDIR /app

# Dependencies installieren
COPY package*.json ./
RUN npm install

# App Code kopieren
COPY . .

# Port freigeben
EXPOSE 3000

# Development Server starten
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
