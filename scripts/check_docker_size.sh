

echo "Building Docker image to check size..."
docker build -t sns-ai-agent:size-check .

echo "Checking image size..."
IMAGE_SIZE=$(docker images sns-ai-agent:size-check --format "{{.Size}}")
echo "Image size: $IMAGE_SIZE"

SIZE_VALUE=$(echo $IMAGE_SIZE | sed 's/[A-Za-z]//g')
SIZE_UNIT=$(echo $IMAGE_SIZE | sed 's/[0-9.]//g')

if [[ "$SIZE_UNIT" == "GB" ]]; then
  SIZE_MB=$(echo "$SIZE_VALUE * 1024" | bc)
elif [[ "$SIZE_UNIT" == "KB" ]]; then
  SIZE_MB=$(echo "$SIZE_VALUE / 1024" | bc)
else
  SIZE_MB=$SIZE_VALUE
fi

echo "Size in MB: $SIZE_MB"

if (( $(echo "$SIZE_MB < 8192" | bc -l) )); then
  echo "✅ Image size is below Fly.io's 8GB limit"
  exit 0
else
  echo "❌ Image size exceeds Fly.io's 8GB limit"
  echo "Please optimize the Docker image further"
  exit 1
fi
