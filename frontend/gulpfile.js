var gulp = require('gulp'), sass = require('gulp-sass');
const theme = "scratch"
gulp.task('css', function () {
	// take files with extension .scss from /scss folder
	return gulp.src('./templates/frontend/'+theme+'/scss/style.scss')
		.pipe(sass({}).on('error', sass.logError)
		)
		// return into css folder
		.pipe(gulp.dest('./static/frontend/'))
});


gulp.task('default', ['css'], function() {
	// watch for CSS changes
	gulp.watch('./templates/frontend/'+theme+'/scss/*.scss', function() {
	
		 // run styles upon changes
		 gulp.run('css');
	});
});