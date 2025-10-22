FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Declare build argument for API URL
ARG VITE_API_BASE_URL

# Set environment variable for Vite to pick up
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Install serve to run the built app
RUN npm install -g serve

# Expose port
EXPOSE 3000

# Serve the built app
CMD ["serve", "-s", "dist", "-l", "3000"]
