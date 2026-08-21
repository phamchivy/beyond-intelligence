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
    options.Limits.MaxRequestBodySize = 150 * 1024 * 1024; // 150 MB
});
builder.Services.Configure<FormOptions>(options =>
{
    options.MultipartBodyLengthLimit = 150 * 1024 * 1024;
});

// 3. CORS cho NuxtJS Frontend
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

// 4. Cấu hình HttpClients kết nối sang Data Pod & Agent Pod
builder.Services.AddHttpClient("DataPod", client =>
{
    client.BaseAddress = new Uri(builder.Configuration["Services:DataPodUrl"] ?? "http://data:8001");
    client.Timeout = TimeSpan.FromSeconds(30);
});

builder.Services.AddHttpClient("AgentPod", client =>
{
    client.BaseAddress = new Uri(builder.Configuration["Services:AgentPodUrl"] ?? "http://agent:8002");
    client.Timeout = TimeSpan.FromSeconds(60); // Đồng bộ reasoning có thể mất 5-15s
});

// 5. Đăng ký Services DI
builder.Services.AddScoped<IDataPodService, DataPodService>();
builder.Services.AddScoped<IS3StorageService, S3StorageService>();
builder.Services.AddScoped<IDataPodClient, DataPodClient>();
builder.Services.AddScoped<IAgentPodClient, AgentPodClient>();

var app = builder.Build();

app.UseCors("AllowFrontend");
app.UseStaticFiles();
app.UseFastEndpoints();
app.UseSwaggerGen();

app.Run();