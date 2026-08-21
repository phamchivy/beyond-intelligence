using FastEndpoints;
using FastEndpoints.Swagger;
using Microsoft.AspNetCore.Http.Features;
using AIHackathonApi.Services;

var builder = WebApplication.CreateBuilder(args);

// 1. FastEndpoints & Swagger
builder.Services.AddFastEndpoints();
builder.Services.SwaggerDocument(o =>
{
    o.DocumentSettings = s =>
    {
        s.Title = "Beyond Intelligence - Orchestrator API";
        s.Version = "v1";
    };
});

// 2. Cấu hình giới hạn dung lượng Upload (150MB)
builder.WebHost.ConfigureKestrel(options =>
{
    options.Limits.MaxRequestBodySize = 150 * 1024 * 1024;
});
builder.Services.Configure<FormOptions>(options =>
{
    options.MultipartBodyLengthLimit = 150 * 1024 * 1024;
});

// 3. CORS cho Frontend
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

// 4. Cấu hình HttpClients kết nối sang Agent Pod (Port 8001) & Data Pod (Port 8002)
builder.Services.AddHttpClient("AgentPod", client =>
{
    var url = builder.Configuration["Services:AgentPodUrl"]
        ?? builder.Configuration["AI_SERVICE_URL"]
        ?? "http://ai:8001";
    client.BaseAddress = new Uri(url);
    client.Timeout = TimeSpan.FromSeconds(60);
});

builder.Services.AddHttpClient("DataPod", client =>
{
    var url = builder.Configuration["Services:DataPodUrl"]
        ?? builder.Configuration["DATA_SERVICE_URL"]
        ?? "http://data:8002";
    client.BaseAddress = new Uri(url);
    client.Timeout = TimeSpan.FromSeconds(60);
});

// 5. Đăng ký Services Dependency Injection
builder.Services.AddScoped<IDataPodService, DataPodService>();
builder.Services.AddScoped<IS3StorageService, S3StorageService>();
builder.Services.AddScoped<IAgentPodClient, AgentPodClient>();
builder.Services.AddScoped<IDataPodClient, DataPodClient>();

var app = builder.Build();

// 6. Middlewares & Routing
app.UseCors("AllowFrontend");
app.UseStaticFiles();
app.UseFastEndpoints();
app.UseSwaggerGen();

// // 7. Health Check Endpoint
// app.MapGet("/health", () => Results.Ok(new 
// { 
//     status = "ok", 
//     service = "backend",
//     timestamp = DateTime.UtcNow 
// }));

app.Run();