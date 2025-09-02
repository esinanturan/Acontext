package blob

import (
	"context"
	"fmt"
	"mime/multipart"
	"net/url"
	"path/filepath"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsCfg "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/feature/s3/manager"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	s3types "github.com/aws/aws-sdk-go-v2/service/s3/types"
	"github.com/memodb-io/Acontext/internal/config"
)

type S3Deps struct {
	Client    *s3.Client
	Uploader  *manager.Uploader
	Presigner *s3.PresignClient
	Bucket    string
	SSE       *s3types.ServerSideEncryption
}

func NewS3(ctx context.Context, cfg *config.Config) (*S3Deps, error) {
	loadOpts := []func(*awsCfg.LoadOptions) error{
		awsCfg.WithRegion(cfg.S3.Region),
	}
	if cfg.S3.AccessKey != "" && cfg.S3.SecretKey != "" {
		loadOpts = append(loadOpts, awsCfg.WithCredentialsProvider(
			credentials.NewStaticCredentialsProvider(cfg.S3.AccessKey, cfg.S3.SecretKey, ""),
		))
	}

	acfg, err := awsCfg.LoadDefaultConfig(ctx, loadOpts...)
	if err != nil {
		return nil, err
	}

	s3Opts := func(o *s3.Options) {
		if ep := strings.TrimSpace(cfg.S3.Endpoint); ep != "" {
			if !strings.HasPrefix(ep, "http://") && !strings.HasPrefix(ep, "https://") {
				ep = "https://" + ep
			}
			if u, uerr := url.Parse(ep); uerr == nil {
				o.BaseEndpoint = aws.String(u.String())
			}
		}
		o.UsePathStyle = cfg.S3.UsePathStyle
	}

	client := s3.NewFromConfig(acfg, s3Opts)
	uploader := manager.NewUploader(client)
	presigner := s3.NewPresignClient(client)

	var sse *s3types.ServerSideEncryption
	if cfg.S3.SSE != "" {
		v := s3types.ServerSideEncryption(cfg.S3.SSE)
		sse = &v
	}

	return &S3Deps{
		Client:    client,
		Uploader:  uploader,
		Presigner: presigner,
		Bucket:    cfg.S3.Bucket,
		SSE:       sse,
	}, nil
}

// Generate a pre-signed PUT URL (recommended for direct uploading of large files)
func (s *S3Deps) PresignPut(ctx context.Context, key, contentType string, expire time.Duration) (string, error) {
	params := &s3.PutObjectInput{
		Bucket:      &s.Bucket,
		Key:         &key,
		ContentType: &contentType,
	}
	if s.SSE != nil {
		params.ServerSideEncryption = *s.SSE
	}
	ps, err := s.Presigner.PresignPutObject(ctx, params, func(po *s3.PresignOptions) {
		po.Expires = expire
	})
	if err != nil {
		return "", err
	}
	return ps.URL, nil
}

// Generate a pre-signed GET URL
func (s *S3Deps) PresignGet(ctx context.Context, key string, expire time.Duration) (string, error) {
	ps, err := s.Presigner.PresignGetObject(ctx, &s3.GetObjectInput{
		Bucket: &s.Bucket,
		Key:    &key,
	}, func(po *s3.PresignOptions) {
		po.Expires = expire
	})
	if err != nil {
		return "", err
	}
	return ps.URL, nil
}

type UploadedMeta struct {
	Bucket string
	Key    string
	ETag   string
	SHA256 string
	MIME   string
	SizeB  int64
}

func (u *S3Deps) UploadFormFile(ctx context.Context, fh *multipart.FileHeader) (*UploadedMeta, error) {
	file, err := fh.Open()
	if err != nil {
		return nil, err
	}
	defer file.Close()

	sumHex, err := sha256OfFileHeader(fh)
	if err != nil {
		return nil, fmt.Errorf("calc sha256: %w", err)
	}

	ext := strings.ToLower(filepath.Ext(fh.Filename))
	datePrefix := time.Now().UTC().Format("2006/01/02")
	key := fmt.Sprintf("uploads/%s/%s%s", datePrefix, sumHex, ext)

	input := &s3.PutObjectInput{
		Bucket:      aws.String(u.Bucket),
		Key:         aws.String(key),
		Body:        file,
		ContentType: aws.String(fh.Header.Get("Content-Type")),
		Metadata: map[string]string{
			"sha256": sumHex,
			"name":   fh.Filename,
		},
	}

	out, err := u.Uploader.Upload(ctx, input)
	if err != nil {
		return nil, err
	}

	return &UploadedMeta{
		Bucket: u.Bucket,
		Key:    key,
		ETag:   *out.ETag,
		SHA256: sumHex,
		MIME:   fh.Header.Get("Content-Type"),
		SizeB:  fh.Size,
	}, nil
}
