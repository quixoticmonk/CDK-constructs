import setuptools

setuptools.setup(
    name="testconstructs",
    version="0.0.1",

    author="Manu Chandrasekhar",

    package_dir={"": "lib"},
    packages=setuptools.find_packages(where="lib"),
        install_requires=[
        "aws-cdk.core==1.91.0",
        "aws-cdk.core==1.91.0",
        "aws-cdk.aws-dynamodb==1.91.0",
        "aws-cdk.aws-apigateway==1.91.0",
        "aws-cdk.aws-lambda==1.91.0",
        "aws-cdk.aws-lambda-event-sources==1.91.0",
        "aws-cdk.aws-iam==1.91.0",
        "aws-cdk.aws-s3==1.91.0",
        "aws-cdk.aws-cloudfront==1.91.0",
        "aws-cdk.aws-cloudfront-origins==1.91.0",
        "aws-cdk.aws-cloudwatch==1.91.0",
        "aws-cdk.aws-sqs==1.91.0",
        "aws-cdk.aws-cloudwatch-actions==1.91.0"
            
    ],
    
)
