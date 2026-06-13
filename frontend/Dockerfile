FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend files
COPY . .

# Expose port
EXPOSE 3000

# Run dev server bound to 0.0.0.0
CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0"]
