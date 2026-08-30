FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY AIHackathonApi.csproj ./
RUN dotnet restore AIHackathonApi.csproj

COPY . ./
RUN dotnet publish AIHackathonApi.csproj -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/publish .
RUN mkdir -p wwwroot/uploads/videos wwwroot/uploads/images

EXPOSE 8000
ENV ASPNETCORE_URLS=http://+:8000
ENTRYPOINT ["dotnet", "AIHackathonApi.dll"]