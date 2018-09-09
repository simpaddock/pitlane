var gulp = require('gulp'), sass = require('gulp-sass');
gulp.task('css', function () {
	// take files with extension .scss from /scss folder
	return gulp.src('./scss/style.scss')
		.pipe(sass({}).on('error', sass.logError)
		)
		// return into css folder
		.pipe(gulp.dest('./static/frontend/'))
});


gulp.task('default', ['css'], function() {
	// watch for CSS changes
	gulp.watch('./scss/*.scss', function() {
		 // run styles upon changes
		 gulp.run('css');
	});
});